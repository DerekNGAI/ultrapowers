import { join } from "path";
import { fileURLToPath } from "url";
import os from "os";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const globalOpenCodeDir = join(os.homedir(), ".config", "opencode");

export default function () {
  return {
    config(cfg) {
      cfg.skills ??= {};
      cfg.skills.paths ??= [];
      cfg.skills.paths.push(join(__dirname, ".opencode", "skills"));

      cfg.agents ??= {};
      cfg.agents.paths ??= [];
      cfg.agents.paths.push(join(globalOpenCodeDir, "agents"));

      return cfg;
    },
  };
}