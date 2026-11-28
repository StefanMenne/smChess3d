// Kampfszene aus den Clips des Rigs rendern (Kampfkamera, vor Grün oder als Tiefenbild), Bild für Bild:
//   node tools/ritter/kampf_rig.mjs <ziel-ordner> <angreifer> <opfer> <angreifer|opfer> '<plan-json>' [bilder=121] [tiefe]
// plan: [{ "anim": "Attack" }, { "anim": "WalkInPlace", "dur": 1.2, "to": "mitte" }, { "anim": "Idle" }]
// -> <ziel>/frame_0000.png ... und <ziel>/frames.zip (für kampf_frames.sh); mit tiefe zusätzlich <ziel>/tiefe.mp4
//    (Steuervideo für control_video: nah hell, fern dunkel)
import { execFileSync, spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { chromium } from '@playwright/test';

const [dir, attacker, victim, role, planJson, frames = '121', depthArg] = process.argv.slice(2);
if (!planJson) { console.error('Aufruf: ziel angreifer opfer rolle plan [bilder] [tiefe]'); process.exit(1); }
const depth = depthArg === 'tiefe';
mkdirSync(dir, { recursive: true });
const PORT = '3126';
const server = spawn('node', ['server.js'], { env: { ...process.env, PORT }, stdio: 'ignore' });
try {
  await new Promise((r) => setTimeout(r, 800));
  const browser = await chromium.launch({ args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=gl'] });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  page.on('pageerror', (e) => console.error(e.message));
  await page.goto(`http://127.0.0.1:${PORT}/?figurensatz=ritter&brett=schnitz`);
  await page.waitForSelector('body[data-ready="1"]', { timeout: 60_000 });
  const n = await page.evaluate((o) => window.chessApp.battleStudioRig(o),
    { attacker, victim, role, plan: JSON.parse(planJson), frames: Number(frames), depth });
  for (let i = 0; i < n; i++) {
    const url = await page.evaluate((k) => window.chessApp.battleStudioRigFrame(k), i);
    writeFileSync(`${dir}/frame_${String(i).padStart(4, '0')}.png`, Buffer.from(url.split(',')[1], 'base64'));
  }
  await browser.close();
  if (depth) {
    execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-framerate', '24', '-i', `${dir}/frame_%04d.png`,
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '12', `${dir}/tiefe.mp4`]);
  } else {
    execFileSync('zip', ['-qj', `${dir}/frames.zip`, ...Array.from({ length: n },
      (_, i) => `${dir}/frame_${String(i).padStart(4, '0')}.png`)]);
  }
  console.log('geschrieben', dir, n, 'Bilder');
} finally {
  server.kill();
}
