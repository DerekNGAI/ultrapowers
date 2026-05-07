import { fileURLToPath } from "node:url";
import path from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default async function ultrapowersPlugin({ client }) {
  client?.app?.log?.("info", {
    plugin: "ultrapowers",
    message: "ultrapowers plugin loaded",
    root: __dirname
  });

  return {
    "shell.env": async () => {
      return {
        ULTRAPOWERS_ROOT: __dirname,
        ULTRAPOWERS_OPENCODE_CONFIG: path.join(__dirname, "opencode.json"),
        ULTRAPOWERS_SKILLS_DIR: path.join(__dirname, "skills"),
        ULTRAPOWERS_PROMPTS_DIR: path.join(__dirname, "prompts")
      };
    }
  };
}