// Startet den Server und öffnet das Spiel in einem Playwright-Chromium-Fenster.
import { chromium } from 'playwright';
import { listen } from './server.js';

const server = await listen(Number(process.env.PORT) || 0);
const url = `http://127.0.0.1:${server.address().port}/`;
console.log(`Schach läuft auf ${url}`);

const context = await chromium.launchPersistentContext('', {
  headless: false,
  viewport: null,
  args: [
    `--app=${url}`,
    '--window-size=1400,900',
    '--ignore-gpu-blocklist',
    '--enable-gpu',
    // Unter Linux sonst oft nur Software-Rendering; Windows/macOS nutzen ihr Standard-Backend
    ...(process.platform === 'linux' ? ['--use-angle=gl'] : []),
  ],
});

const shutdown = async () => {
  server.close();
  await context.close().catch(() => {});
  process.exit(0);
};
context.on('close', shutdown);
context.on('page', (p) => p.on('close', () => context.pages().length === 0 && shutdown()));
for (const p of context.pages()) p.on('close', () => context.pages().length === 0 && shutdown());
process.on('SIGINT', shutdown);
