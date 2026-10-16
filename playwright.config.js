import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:3123',
    viewport: { width: 1400, height: 900 },
    // Echte GPU nutzen – mit Software-Rendering ist die Szene viel zu langsam
    launchOptions: { args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=gl'] },
  },
  webServer: {
    command: 'node server.js',
    url: 'http://127.0.0.1:3123',
    env: { PORT: '3123' },
    reuseExistingServer: false,
  },
});
