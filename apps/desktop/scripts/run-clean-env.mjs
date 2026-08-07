#!/usr/bin/env node
// Cross-platform replacement for `env -u VAR ... cmd` (not available on Windows).
// Usage: node scripts/run-clean-env.mjs VAR1 VAR2 -- <command> [args...]
import { spawn } from "node:child_process";

const args = process.argv.slice(2);
const sepIndex = args.indexOf("--");
if (sepIndex === -1) {
  console.error("Usage: run-clean-env.mjs VAR1 VAR2 -- <command> [args...]");
  process.exit(1);
}

const varsToUnset = args.slice(0, sepIndex);
const command = args.slice(sepIndex + 1);

const env = { ...process.env };
for (const key of varsToUnset) {
  delete env[key];
}

const child = spawn(command[0], command.slice(1), {
  env,
  stdio: "inherit",
  shell: process.platform === "win32",
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code ?? 0);
  }
});
