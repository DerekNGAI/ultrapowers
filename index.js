import { join } from "path";
import { fileURLToPath } from "url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

export default function (ctx) {
  return {
    config(cfg) {
      // Register the bundled skills directory
      cfg.skills ??= {};
      cfg.skills.paths ??= [];
      cfg.skills.paths.push(join(__dirname, ".opencode", "skills"));

      // Register bundled agents
      cfg.agents ??= {};
      cfg.agents.paths ??= [];
      cfg.agents.paths.push(join(__dirname, ".opencode", "agents"));

      return cfg;
    },
  };
}