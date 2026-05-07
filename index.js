import { join } from "path";
import { fileURLToPath } from "url";
import { readFileSync, existsSync } from "fs";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

function loadPackageConfig() {
  const configPath = join(__dirname, "opencode.json");

  if (!existsSync(configPath)) return {};

  try {
    return JSON.parse(readFileSync(configPath, "utf8"));
  } catch (error) {
    throw new Error(`Failed to parse ultrapowers opencode.json: ${error.message}`);
  }
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

      const packageConfig = loadPackageConfig();

      if (packageConfig.agent) {
        for (const [name, agentDef] of Object.entries(packageConfig.agent)) {
          cfg.agent[name] = {
            ...agentDef,
            ...(agentDef.prompt
              ? {
                  prompt: agentDef.prompt.replace(
                    "{file:",
                    `{file:${__dirname}/`
                  ),
                }
              : {}),
          };
        }
      }

      if (packageConfig.default_agent && !cfg.default_agent) {
        cfg.default_agent = packageConfig.default_agent;
      }

      return cfg;
    },
  };
}