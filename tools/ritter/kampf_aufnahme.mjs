// Kampfszene im Spiel in Echtzeit mitschneiden (zum Ansehen, nicht für das Spiel):
//   node tools/ritter/kampf_aufnahme.mjs <ziel.webm>
// Stellung nach 1. e4 d5, Weiß schlägt exd5; Aufnahme von der Kamerafahrt bis zurück in die Startansicht.
import { spawn } from 'node:child_process';
import { copyFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { chromium } from '@playwright/test';

const out = process.argv[2];
if (!out) { console.error('Ziel fehlt'); process.exit(1); }
const PORT = '3125';
const server = spawn('node', ['server.js'], { env: { ...process.env, PORT }, stdio: 'ignore' });
try {
  await new Promise((r) => setTimeout(r, 800));
  const dir = mkdtempSync(join(tmpdir(), 'kampf-'));
  const browser = await chromium.launch({ args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=gl'] });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, recordVideo: { dir, size: { width: 1400, height: 900 } } });
  const page = await ctx.newPage();
  await page.goto(`http://127.0.0.1:${PORT}/?figurensatz=ritter&brett=schnitz`);
  await page.waitForSelector('body[data-ready="1"]', { timeout: 60_000 });
  await page.evaluate(() => window.chessApp.newGame('rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2'));
  await page.waitForTimeout(1500);
  const click = async (sq) => {
    const p = await page.evaluate((s) => window.chessApp.squareToScreen(s), sq);
    await page.mouse.click(p.x, p.y);
  };
  await click('e4');
  await click('d5');
  await page.waitForFunction(() => window.chessApp.battleState().phase === 'anlauf');
  await page.waitForFunction(() => window.chessApp.battleState().phase === null, null, { timeout: 60_000 });
  await page.waitForTimeout(1500);
  const video = page.video();
  await ctx.close();
  copyFileSync(await video.path(), out);
  await browser.close();
  console.log('geschrieben', out);
} finally {
  server.kill();
}
