const path = require("node:path");

const venvBin =
  process.platform === "win32"
    ? path.join(__dirname, ".venv", "Scripts")
    : path.join(__dirname, ".venv", "bin");
const webPort = Number(process.env.VSF_E2E_PORT || 8765);
const webBaseUrl = `http://127.0.0.1:${webPort}`;

const webCommand =
  process.platform === "win32"
    ? `set "PATH=${venvBin};%PATH%" && vsf-profiler web --port ${webPort}`
    : `PATH="${venvBin}:$PATH" vsf-profiler web --port ${webPort}`;

/** @type {import('@playwright/test').PlaywrightTestConfig} */
module.exports = {
  testDir: "./tests/e2e",
  timeout: 90_000,
  expect: {
    timeout: 20_000,
  },
  reporter: [["list"]],
  use: {
    baseURL: webBaseUrl,
    trace: "retain-on-failure",
  },
  webServer: {
    command: webCommand,
    url: `${webBaseUrl}/api/health`,
    reuseExistingServer: false,
    timeout: 30_000,
  },
};
