import { join } from "path";
import { fileURLToPath } from "url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

export default function () {
  return {
    config(cfg) {
      // Ensure skills paths include your local .opencode/skills
      cfg.skills ??= {};
      cfg.skills.paths ??= [];
      cfg.skills.paths.push(join(__dirname, ".opencode", "skills"));

      // Ensure agent prompts are discovered from .opencode/prompts
      cfg.agents ??= {};
      cfg.agents.paths ??= [];
      cfg.agents.paths.push(join(__dirname, ".opencode", "prompts"));

      return cfg;
    },
  };
}