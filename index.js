import { join } from "path";
import { fileURLToPath } from "url";
import { existsSync, readFileSync } from "fs";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

function loadJSONConfig() {
  const file = join(__dirname, "opencode.json");
  if (!existsSync(file)) return {};

  const raw = readFileSync(file, "utf8");
  return JSON.parse(raw);
}

function resolveFileRefs(value) {
  if (typeof value === "string") {
    return value.replace(/\{file:([^}]+)\}/g, (_, p) => {
      const abs = join(__dirname, p);
      if (existsSync(abs)) {
        return readFileSync(abs, "utf8");
      }
      return `{file:${p}}`; // fallback
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
      if (!cfg.skills.paths.includes(skillsPath)) {
        cfg.skills.paths.push(skillsPath);
      }

      // Only add agents path if it exists
      const agentsPath = join(__dirname, ".opencode", "agents");
      if (existsSync(agentsPath) && !cfg.agents.paths.includes(agentsPath)) {
        cfg.agents.paths.push(agentsPath);
      }

      const packaged = resolveFileRefs(loadJSONConfig());

      console.log("=== Ultrapowers Config Debug ===");
      console.log("Loaded from opencode.json:", JSON.stringify(packaged, null, 2));
      console.log("Final agent config being merged:", JSON.stringify(packaged.agent || {}, null, 2));

      // Better merging for agents
      if (packaged.agent) {
        cfg.agent = {
          ...cfg.agent,
          ...packaged.agent
        };

        // Some versions of OpenCode also look here
        cfg.agents.custom = {
          ...cfg.agents.custom,
          ...packaged.agent
        };
      }

      if (packaged.default_agent && !cfg.default_agent) {
        cfg.default_agent = packaged.default_agent;
      }

      return cfg;
    }
  };
}