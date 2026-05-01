import { join } from "path";
import { fileURLToPath } from "url";
import os from "os";
import { mkdirSync } from "fs";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const globalOpenCodeDir = join(os.homedir(), ".config", "opencode");
const globalAgentsDir = join(globalOpenCodeDir, "agents");
const localSkillsDir = join(__dirname, ".opencode", "skills");

export default function () {
  return {
    config(cfg) {
      mkdirSync(globalAgentsDir, { recursive: true });

      cfg.skills ??= {};
      cfg.skills.paths ??= [];
      if (!cfg.skills.paths.includes(localSkillsDir)) {
        cfg.skills.paths.push(localSkillsDir);
      }

      cfg.agents ??= {};
      cfg.agents.paths ??= [];
      if (!cfg.agents.paths.includes(globalAgentsDir)) {
        cfg.agents.paths.push(globalAgentsDir);
      }

      return cfg;
    },
  };
}