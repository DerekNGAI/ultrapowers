import { join } from "path";
import { fileURLToPath } from "url";
import { existsSync, readFileSync, appendFileSync } from "fs";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

function debugLog(...args) {
  const timestamp = new Date().toISOString();
  const message = `[${timestamp}] ${args.join(" ")}\n`;
  try {
    appendFileSync(join(__dirname, "ultrapowers-debug.log"), message);
    console.log(...args);
  } catch (e) {}
}

function loadJSONConfig() {
  const possiblePaths = [
    join(__dirname, "opencode.json"),
    join(__dirname, ".opencode", "opencode.json"),
    join(process.cwd(), "opencode.json"),
  ];

  for (const file of possiblePaths) {
    debugLog(`[DEBUG] Checking opencode.json at: ${file}`);
    if (existsSync(file)) {
      try {
        const raw = readFileSync(file, "utf8");
        const parsed = JSON.parse(raw);
        debugLog(`[DEBUG] Successfully loaded opencode.json from: ${file}`);
        return parsed;
      } catch (err) {
        debugLog(`[ERROR] Failed to parse ${file}:`, err.message);
      }
    }
  }

  debugLog("[DEBUG] opencode.json NOT FOUND in any location");
  return {};
}

function resolveFileRefs(value) {
  if (typeof value === "string") {
    return value.replace(/\{file:([^}]+)\}/g, (_, p) => {
      const abs = join(__dirname, p);
      debugLog(`[DEBUG] Resolving file reference: ${p} → ${abs}`);

      if (existsSync(abs)) {
        try {
          const content = readFileSync(abs, "utf8").trim();
          debugLog(`[DEBUG] Successfully read prompt file (${content.length} characters)`);
          return content;                    // Inline the actual prompt content
        } catch (e) {
          debugLog(`[ERROR] Failed to read ${abs}:`, e.message);
          return `{file:${p}} (read failed)`;
        }
      } else {
        debugLog(`[WARN] Prompt file not found: ${abs}`);
        return `{file:${p}} (not found)`;
      }
    });
  }

  if (Array.isArray(value)) {
    return value.map(resolveFileRefs);
  }

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

      debugLog("=== Ultrapowers Config Debug ===");
      debugLog("Raw loaded from opencode.json:", JSON.stringify(packaged, null, 2));
      debugLog("Resolved agents with prompts:", JSON.stringify(packaged.agent || {}, null, 2));

      if (packaged.agent) {
        debugLog("Merging agents into cfg...");
        cfg.agent = {
          ...cfg.agent,
          ...packaged.agent
        };

        cfg.agents.custom = {
          ...cfg.agents.custom,
          ...packaged.agent
        };
      }

      if (packaged.default_agent && !cfg.default_agent) {
        cfg.default_agent = packaged.default_agent;
      }

      debugLog("Final merged cfg.agent:", JSON.stringify(cfg.agent, null, 2));

      return cfg;
    }
  };
}