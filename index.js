import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { existsSync, readFileSync, appendFileSync } from "fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function debugLog(...args) {
  try {
    const timestamp = new Date().toISOString();
    appendFileSync(join(__dirname, "ultrapowers-debug.log"), 
      `[${timestamp}] ${args.join(" ")}\n`);
  } catch (e) {}
}

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

export default function ultrapowers() {
  return {
    config(cfg) {
      cfg ??= {};
      cfg.skills ??= {};
      cfg.skills.paths ??= [];
      cfg.agents ??= {};
      cfg.agents.paths ??= [];
      cfg.agent ??= {};
      cfg.agents.custom ??= {};

      const skillsPath = join(__dirname, ".opencode", "skills");
      const agentsPath = join(__dirname, ".opencode", "agents");

      if (!cfg.skills.paths.includes(skillsPath)) {
        cfg.skills.paths.push(skillsPath);
      }

      if (existsSync(agentsPath) && !cfg.agents.paths.includes(agentsPath)) {
        cfg.agents.paths.push(agentsPath);
      }

      const packaged = resolveFileRefs(loadJSONConfig());

      if (packaged.agent) {
        cfg.agent = { ...cfg.agent, ...packaged.agent };
        cfg.agents.custom = { ...cfg.agents.custom, ...packaged.agent };
      }

      if (packaged.default_agent && !cfg.default_agent) {
        cfg.default_agent = packaged.default_agent;
      }

      return cfg;
    }
  };
}