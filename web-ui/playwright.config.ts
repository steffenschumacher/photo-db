import { defineConfig, devices } from '@playwright/test';

const backendServer = {
  command: '../.venv/bin/python e2e/backend.py',
  url: 'http://127.0.0.1:5000/web-config',
  timeout: 60_000,
  reuseExistingServer: false,
};
const angularServer = {
  command: 'npm start -- --host 127.0.0.1',
  url: 'http://127.0.0.1:4200',
  timeout: 120_000,
  reuseExistingServer: false,
};

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 60_000 },
  use: { baseURL: 'http://127.0.0.1:4200', trace: 'retain-on-failure' },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-safari', use: { ...devices['iPhone 13'] } },
  ],
  webServer:
    process.env['E2E_EXTERNAL_BACKEND'] === '1' ? angularServer : [backendServer, angularServer],
});
