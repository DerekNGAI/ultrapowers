import { join, dirname, resolve, isAbsolute } from "path";
import { fileURLToPath } from "url";
import { existsSync, readFileSync, lstatSync, mkdirSync, realpathSync, statSync, accessSync, constants, writeFileSync, chmodSync, linkSync, renameSync, rmSync } from "fs";
import { homedir } from "node:os";
import { randomUUID } from "node:crypto";
import { parse, modify, applyEdits } from "jsonc-parser";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function loadJSONConfig() {
  const possiblePaths = [
    join(__dirname, "opencode.json"),
    join(__dirname, ".opencode", "opencode.json"),
  ];

  for (const file of possiblePaths) {
    if (existsSync(file)) {
      try {
        const raw = readFileSync(file, "utf8");
        return JSON.parse(raw);
      } catch (err) {}
    }
  }
  return {};
}

function resolveFileRefs(value) {
  if (typeof value === "string") {
    return value.replace(/\{file:([^}]+)\}/g, (_, p) => {
      const candidates = [
        join(__dirname, p),
        join(__dirname, ".opencode", p),
        join(__dirname, "prompts", p),
      ];

      for (const abs of candidates) {
        if (existsSync(abs)) {
          try {
            return readFileSync(abs, "utf8").trim();
          } catch (e) {}
        }
      }
      return `{file:${p}} (not found)`;
    });
  }

  if (Array.isArray(value)) return value.map(resolveFileRefs);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([k, v]) => [k, resolveFileRefs(v)])
    );
  }
  return value;
}

function mergeDefaults(defaults, overrides) {
  if (!overrides || typeof overrides !== "object" || Array.isArray(overrides)) return overrides ?? defaults;
  // Preserve a shorthand permission when adding narrower pattern overrides.
  if (["allow", "ask", "deny"].includes(defaults)) defaults = { "*": defaults };
  const merged = { ...defaults };
  for (const [key, value] of Object.entries(overrides)) {
    merged[key] = mergeDefaults(defaults?.[key], value);
  }
  return merged;
}

const reviewers = ["ultrapowers-reviewer-a", "ultrapowers-reviewer-b"];

function ensureReviewerTemplates(files, file) {
  const isRecord = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
  const agents = {};
  let before;
  let hasSchema = false;
  for (const path of files) {
    let text;
    try {
      text = readFileSync(path, "utf8");
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
      // A dangling symlink is an existing user file, not a missing config.
      try { lstatSync(path); } catch (missing) {
        if (missing.code === "ENOENT") continue;
        throw missing;
      }
      throw error;
    }
    const errors = [];
    const parsed = parse(text, errors, { allowTrailingComma: true });
    if (errors.length || !isRecord(parsed) || (parsed.agent !== undefined && !isRecord(parsed.agent))) {
      throw new Error(`Invalid OpenCode config in ${path}; reviewer templates were not written.`);
    }
    for (const name of reviewers) {
      const agent = parsed.agent?.[name];
      if (agent === undefined) continue;
      if (!isRecord(agent)) throw new Error(`Invalid agent.${name} in ${path}; reviewer templates were not written.`);
      agents[name] = { ...agents[name], ...agent };
    }
    if (path === file) {
      before = text;
      hasSchema = Object.hasOwn(parsed, "$schema");
    }
  }

  let after = before ?? "{}\n";
  const options = {
    // Prepend fields so trailing comments stay with their original properties.
    getInsertionIndex: () => 0,
    formattingOptions: { insertSpaces: true, tabSize: 2, eol: after.includes("\r\n") ? "\r\n" : "\n" },
  };
  if (!hasSchema) after = applyEdits(after, modify(after, ["$schema"], "https://opencode.ai/config.json", options));
  for (const name of reviewers) {
    for (const [key, value] of Object.entries({ mode: "subagent", model: "" })) {
      if (Object.hasOwn(agents[name] ?? {}, key)) continue;
      after = applyEdits(after, modify(after, ["agent", name, key], value, options));
    }
  }
  if (after === before) return false;

  mkdirSync(dirname(file), { recursive: true, mode: 0o700 });
  const target = before === undefined ? file : realpathSync(file);
  if (before !== undefined) accessSync(target, constants.W_OK);
  const temporary = join(dirname(target), `.ultrapowers-${randomUUID()}.tmp`);
  try {
    writeFileSync(temporary, after, { flag: "wx", mode: 0o600 });
    chmodSync(temporary, before === undefined ? 0o600 : statSync(target).mode & 0o777);
    if (before === undefined) {
      // Creating a config must not replace one created by another process.
      linkSync(temporary, target);
    } else {
      if (realpathSync(file) !== target || readFileSync(file, "utf8") !== before) {
        throw new Error(`OpenCode config changed during template setup: ${file}. Restart OpenCode to retry.`);
      }
      renameSync(temporary, target);
    }
  } finally {
    rmSync(temporary, { force: true });
  }
  return true;
}

export default function ultrapowers({ client } = {}) {
  const xdg = process.env.XDG_CONFIG_HOME;
  const configDirectory = join(xdg && isAbsolute(xdg) ? xdg : join(homedir(), ".config"), "opencode");
  const globalFiles = ["config.json", "opencode.json", "opencode.jsonc"].map((name) => join(configDirectory, name));
  const templatePath = globalFiles.findLast((path) => existsSync(path)) ?? globalFiles[1];
  let templateError;
  let config;
  const runs = new Map();

  async function preflight() {
    const models = reviewers.map((name) => {
      const agent = config?.agent?.[name];
      const model = agent?.model;
      if (agent?.disable || agent?.mode !== "subagent" || typeof model !== "string" || !/^[^/\s]+\/\S+$/.test(model)) {
        throw new Error(`${templateError ? `${templateError}\n` : ""}Configure agent.${name}.model as an available provider/model ID (mode: subagent, enabled) in ${templatePath} or your project config. Set both reviewer model IDs using opencode models, then quit and restart OpenCode before dual-review.`);
      }
      return model;
    });
    if (models[0] === models[1]) throw new Error("Dual-review requires two different model families; both reviewers use the same model.");
    const { data } = await client.provider.list({ throwOnError: true });
    if (!data) throw new Error("Cannot inspect connected models for dual-review.");
    const families = models.map((model) => {
      const slash = model.indexOf("/");
      const providerID = model.slice(0, slash);
      const modelID = model.slice(slash + 1);
      const metadata = data.all.find((provider) => provider.id === providerID)?.models[modelID];
      if (!data.connected.includes(providerID) || !metadata) {
        throw new Error(`Reviewer model ${model} is not available from a connected provider.`);
      }
      if (!metadata.capabilities?.toolcall) throw new Error(`Reviewer model ${model} must support tool calls to inspect the repo.`);
      const family = (config.provider?.[providerID]?.models?.[modelID]?.family || metadata.family || "").trim().toLowerCase();
      if (!family) throw new Error(`Model ${model} has no family metadata. Set provider.${providerID}.models[${JSON.stringify(modelID)}].family in your OpenCode config.`);
      return family;
    });
    if (families[0] === families[1]) throw new Error(`Dual-review requires different model families; both are ${families[0]}.`);
    return models.map((model, i) => `${reviewers[i]}: ${model} (family: ${families[i]}, IDs: ${i === 0 ? "A" : "B"}-001 onward)`).join("\n");
  }

  function startReview(sessionID) {
    const run = { counts: [0, 0], ready: preflight() };
    runs.set(sessionID, run);
    return run;
  }

  async function prepare(sessionID, output) {
    const run = startReview(sessionID);
    let text;
    try {
      const models = await run.ready;
      text = `Dual-review preflight passed:\n${models}\nMaximum 3 review rounds, one rebuttal per reviewer per round, and 6 calls per reviewer total. Follow the shared dual-review protocol.`;
    } catch (error) {
      text = `Dual-review preflight failed: ${error instanceof Error ? error.message : "Unable to inspect reviewer configuration."}\nStop this workflow without edits or reviewer calls. Report INCOMPLETE with this setup requirement to the user.`;
    }
    output.parts.push({
      type: "text",
      synthetic: true,
      text,
      ...(output.message && {
        id: `prt_${randomUUID().replaceAll("-", "")}`,
        sessionID,
        messageID: output.message.id,
      }),
    });
  }

  return {
    config(cfg) {
      templateError = undefined;
      try {
        if (ensureReviewerTemplates(globalFiles, templatePath)) {
          // SDK requests may wait for plugin initialization; never await them here.
          void client?.tui?.showToast?.({ body: {
            variant: "info",
            message: `Reviewer templates added to ${templatePath}. Choose models using opencode models, then quit and restart OpenCode.`,
          } })?.catch(() => {});
        }
      } catch (error) {
        templateError = `Automatic reviewer template setup failed for ${templatePath}: ${error.message}`;
        void client?.app?.log?.({ body: { service: "ultrapowers", level: "warn", message: templateError } })?.catch(() => {});
      }
      cfg ??= {};
      cfg.skills ??= {};
      cfg.skills.paths ??= [];
      cfg.agent ??= {};

      const skillsPath = join(__dirname, ".opencode", "skills");

      if (!cfg.skills.paths.includes(skillsPath)) {
        cfg.skills.paths.push(skillsPath);
      }

      const packaged = resolveFileRefs(loadJSONConfig());

      for (const [name, defaults] of Object.entries(packaged.agent ?? {})) {
        cfg.agent[name] = mergeDefaults(defaults, cfg.agent[name]);
      }
      cfg.command = mergeDefaults(packaged.command ?? {}, cfg.command);
      cfg.instructions = [...new Set([
        ...(cfg.instructions ?? []),
        ...(packaged.instructions ?? []).map((path) => resolve(__dirname, path)),
      ])];

      if (packaged.default_agent && !cfg.default_agent) {
        cfg.default_agent = packaged.default_agent;
      }

      config = cfg;
    },
    async "command.execute.before"(input, output) {
      if (input.command === "dual-review") await prepare(input.sessionID, output);
    },
    async "chat.message"(input, output) {
      if (input.agent !== "ultrapowers-build") return;
      // Synthetic continuation messages must preserve the current call budget.
      if (output.parts.length && output.parts.every((part) => part.synthetic)) return;
      await prepare(input.sessionID, output);
    },
    async "tool.execute.before"(input, output) {
      if (input.tool !== "task") return;
      const slot = reviewers.indexOf(output.args.subagent_type);
      if (slot === -1) return;
      if (output.args.background) throw new Error("Dual-review uses concurrent foreground tasks; wait for both results before changing code.");
      const run = runs.get(input.sessionID) ?? startReview(input.sessionID);
      await run.ready;
      if (run.counts[slot] >= 6) throw new Error("Dual-review call limit reached. Stop spawning reviewers and summarize the final verdict and unresolved findings.");
      run.counts[slot]++;
    },
    async event({ event }) {
      if (event.type === "session.deleted") runs.delete(event.properties.info.id);
    },
  };
}
