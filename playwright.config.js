const path = require("node:path");

const venvBin =
  process.platform === "win32"
    ? path.join(__dirname, ".venv", "Scripts")
    : path.join(__dirname, ".venv", "bin");

const webCommand =
  process.platform === "win32"
    ? `set "PATH=${venvBin};%PATH%" && vsf-profiler web --port 8765`
    : `PATH="${venvBin}:$PATH" vsf-profiler web --port 8765`;

/** @type {import('@playwright/test').PlaywrightTestConfig} */
module.exports = {
  testDir: "./tests/e2e",
  timeout: 90_000,
  expect: {
    timeout: 20_000,
  },
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8765",
    trace: "retain-on-failure",
  },
  webServer: {
    command: webCommand,
    url: "http://127.0.0.1:8765/api/health",
    reuseExistingServer: false,
    timeout: 30_000,
  },
};
