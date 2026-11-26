// Startet den Server und öffnet das Spiel in einem Playwright-Chromium-Fenster.
import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { listen } from './server.js';

// Fester Port und festes Browser-Profil: Die Seite speichert Figurensatz, Brett, Einstellungen und die laufende
// Partie im localStorage, und der gehört zu Profil und Origin (mit Port). Mit leerem Profil oder zufälligem Port
// wäre beim nächsten Start alles wieder auf Standard.
const PORT = Number(process.env.PORT) || 3417;
const PROFILE = path.join(path.dirname(fileURLToPath(import.meta.url)), '.browser-profil');

let server;
try {
  server = await listen(PORT);
} catch (e) {
  if (e.code !== 'EADDRINUSE') throw e;
  server = await listen(0);
  console.warn(`Port ${PORT} ist belegt, nehme ${server.address().port} (Auswahl und Partie werden dann nicht wiederhergestellt)`);
}
const url = `http://127.0.0.1:${server.address().port}/`;
console.log(`Schach läuft auf ${url}`);

const options = {
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
};
let context;
try {
  context = await chromium.launchPersistentContext(PROFILE, options);
} catch (e) {
  // Profil gesperrt (Spiel läuft schon in einem anderen Fenster): mit leerem Profil starten
  console.warn(`Browser-Profil nicht nutzbar (${e.message.split('\n')[0]}), starte ohne gespeicherte Einstellungen`);
  context = await chromium.launchPersistentContext('', options);
}

const shutdown = async () => {
  server.close();
  await context.close().catch(() => {});
  process.exit(0);
};
context.on('close', shutdown);
context.on('page', (p) => p.on('close', () => context.pages().length === 0 && shutdown()));
for (const p of context.pages()) p.on('close', () => context.pages().length === 0 && shutdown());
process.on('SIGINT', shutdown);
