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
      return `{file:${abs}}`;
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

      const skillsPath = join(__dirname, ".opencode", "skills");
      const agentsPath = join(__dirname, ".opencode", "agents");

      if (!cfg.skills.paths.includes(skillsPath)) {
        cfg.skills.paths.push(skillsPath);
      }

      if (!cfg.agents.paths.includes(agentsPath)) {
        cfg.agents.paths.push(agentsPath);
      }

      const packaged = resolveFileRefs(loadJSONConfig());

      if (packaged.agent) {
        cfg.agent = {
          ...packaged.agent,
          ...cfg.agent
        };
      }

      if (packaged.default_agent && !cfg.default_agent) {
        cfg.default_agent = packaged.default_agent;
      }

      return cfg;
    }
  };
}