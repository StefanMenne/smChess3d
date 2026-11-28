// Start- und Endbild einer Kampfszene aus der Kampfkamera vor Grün rendern (Vorlagen für generate_video):
//   node tools/ritter/kampf_studio.mjs <ziel-ordner> [angreifer=wp] [opfer=bp] [groesse=1024]
// -> <ziel>/start.png (beide Figuren in ihren Ecken), <ziel>/angreifer.png und <ziel>/opfer.png (je allein in seiner
//    Ecke, für getrennte Angriffs- und Sterbevideos), <ziel>/ende.png (Angreifer allein in der Mitte)
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { chromium } from '@playwright/test';

const [dir, attacker = 'wp', victim = 'bp', size = '1024'] = process.argv.slice(2);
if (!dir) { console.error('Ordner fehlt'); process.exit(1); }
mkdirSync(dir, { recursive: true });
const PORT = '3124';
const server = spawn('node', ['server.js'], { env: { ...process.env, PORT }, stdio: 'ignore' });
try {
  await new Promise((r) => setTimeout(r, 800));
  const browser = await chromium.launch({ args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=gl'] });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  page.on('pageerror', (e) => console.error(e.message));
  for (const phase of ['start', 'angreifer', 'opfer', 'ende']) {
    await page.goto(`http://127.0.0.1:${PORT}/?figurensatz=ritter&brett=schnitz`);
    await page.waitForSelector('body[data-ready="1"]', { timeout: 60_000 });
    const url = await page.evaluate((o) => window.chessApp.battleStudio(o),
      { attacker, victim, phase: phase === 'ende' ? 'end' : phase, size: Number(size) });
    writeFileSync(`${dir}/${phase}.png`, Buffer.from(url.split(',')[1], 'base64'));
    console.log('geschrieben', `${dir}/${phase}.png`);
  }
  await browser.close();
} finally {
  server.kill();
}
