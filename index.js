import { join } from "path";
import { fileURLToPath } from "url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

export default function ultrapowers() {
  return {
    config(cfg) {
      cfg ??= {};

      cfg.skills ??= {};
      cfg.skills.paths ??= [];

      cfg.agents ??= {};
      cfg.agents.paths ??= [];

      const skillsPath = join(__dirname, ".opencode", "skills");
      const agentsPath = join(__dirname, ".opencode", "agents");
      const promptsPath = join(__dirname, ".opencode", "prompts");

      if (!cfg.skills.paths.includes(skillsPath)) {
        cfg.skills.paths.push(skillsPath);
      }

      if (!cfg.agents.paths.includes(agentsPath)) {
        cfg.agents.paths.push(agentsPath);
      }

      if (!cfg.agents.paths.includes(promptsPath)) {
        cfg.agents.paths.push(promptsPath);
      }

      return cfg;
    },
  };
}