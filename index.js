import { join } from "path";
import { fileURLToPath } from "url";
import os from "os";
import { mkdirSync, existsSync, readdirSync, copyFileSync } from "fs";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const globalOpenCodeDir = join(os.homedir(), ".config", "opencode");
const globalAgentsDir = join(globalOpenCodeDir, "agents");
const localAgentsDir = join(__dirname, ".opencode", "agents");

export default function () {
  return {
    config(cfg) {
      mkdirSync(globalAgentsDir, { recursive: true });

      if (existsSync(localAgentsDir)) {
        for (const file of readdirSync(localAgentsDir)) {
          if (file.endsWith(".md")) {
            copyFileSync(
              join(localAgentsDir, file),
              join(globalAgentsDir, file)
            );
          }
        }
      }

      cfg.skills ??= {};
      cfg.skills.paths ??= [];
      cfg.skills.paths.push(join(__dirname, ".opencode", "skills"));

      cfg.agents ??= {};
      cfg.agents.paths ??= [];
      cfg.agents.paths.push(globalAgentsDir);

      return cfg;
    },
  };
}