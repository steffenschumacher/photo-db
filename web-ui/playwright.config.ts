import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 60_000 },
  use: { baseURL: 'http://127.0.0.1:4200', trace: 'retain-on-failure' },
  webServer: [
    {
      command: '../.venv/bin/python e2e/backend.py',
      url: 'http://127.0.0.1:5000/web-config',
      timeout: 60_000,
      reuseExistingServer: false,
    },
    {
      command: 'npm start -- --host 127.0.0.1',
      url: 'http://127.0.0.1:4200',
      timeout: 120_000,
      reuseExistingServer: false,
    },
  ],
});
