import { test, expect } from '@playwright/test';

// Kampfszenen (Ritter, wie Battle Chess): Anlauf in die Ecken, Kampfkamera, Video statt der zwei Figuren, zurück.
const SHOTS = 'konzepte/web_shots';
test.describe.configure({ timeout: 180_000 });

async function clickSquare(page, sq) {
  const { x, y } = await page.evaluate((s) => {
    for (const h of [0, 0.3, 0.6, 0.9, 1.2]) {
      const p = window.chessApp.squareToScreen(s, h);
      if (window.chessApp.squareAtScreen(p.x, p.y) === s) return p;
    }
    return window.chessApp.squareToScreen(s);
  }, sq);
  await page.mouse.click(x, y);
}

const state = (page) => page.evaluate(() => window.chessApp.battleState());

test('Ritter: weißer Bauer schlägt schwarzen Bauern mit Kampfvideo (exd5)', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  await page.goto('/?figurensatz=ritter&brett=schnitz');
  await page.waitForSelector('body[data-ready="1"]', { timeout: 60_000 });
  await page.getByTestId('level').selectOption('1');
  // 1. e4 d5, Weiß am Zug
  await page.evaluate(() => window.chessApp.newGame('rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2'));
  await page.evaluate(() => window.chessApp.battleStepping(true));
  await page.waitForTimeout(1200);
  const home = await page.evaluate(() => window.chessApp.squareToScreen('d5'));
  await clickSquare(page, 'e4');
  await clickSquare(page, 'd5');

  await page.waitForFunction(() => window.chessApp.battleState().phase === 'anlauf');
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${SHOTS}/kampf_1_anlauf.png` });

  // Haltepunkte: Übergänge Szene -> Video und Video -> Szene müssen deckungsgleich sein (Bilder vergleichen)
  const step = async (phase, shot) => {
    await page.waitForFunction((p) => window.chessApp.battleState().phase === p, phase, { timeout: 30_000 });
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${SHOTS}/${shot}.png` });
  };
  await step('bereit', 'kampf_2_vorher');
  await page.evaluate(() => window.chessApp.battleContinue());
  await step('video', 'kampf_3_video_erstes');
  // Video: beide Figuren sind ersetzt, das Feld liegt exakt in der Bildmitte, das Video sitzt über der Mitte
  const s = await state(page);
  const centre = await page.evaluate(() => window.chessApp.squareToScreen('d5'));
  expect(Math.abs(centre.x - (s.scene.left + s.scene.width / 2))).toBeLessThan(0.5);
  expect(Math.abs(centre.y - (s.scene.top + s.scene.height / 2))).toBeLessThan(0.5);
  expect(Math.abs(s.canvas.left + s.canvas.width / 2 - centre.x)).toBeLessThan(1);
  expect(s.canvas.height).toBeCloseTo(s.scene.height * 0.85, 0);
  expect(await page.evaluate(() => window.chessApp.pieceCount())).toBe(30);   // Angreifer zählt erst nach dem Zug
  expect(s.frame).toBe(0);
  await page.evaluate(() => window.chessApp.battleContinue());
  await page.waitForFunction(() => window.chessApp.battleState().frame >= 40);
  await page.screenshot({ path: `${SHOTS}/kampf_4_video_mitte.png` });
  await step('videoEnde', 'kampf_5_video_letztes');
  await page.evaluate(() => window.chessApp.battleContinue());
  await step('sieger', 'kampf_6_nachher');
  expect((await state(page)).canvas).toBeNull();
  await page.evaluate(() => window.chessApp.battleContinue());
  await page.waitForFunction(() => window.chessApp.battleState().phase === null, null, { timeout: 15_000 });
  await page.waitForFunction(() => window.chessApp.isIdle() && window.chessApp.history().length === 2, null,
    { timeout: 60_000 });
  expect(await page.evaluate(() => window.chessApp.history()[0])).toBe('exd5');   // Historie ab der FEN
  expect(await page.evaluate(() => window.chessApp.pieceAt('d5'))).toMatch(/^(wp|b.)$/);   // Schwarz darf zurückschlagen
  const back = await page.evaluate(() => window.chessApp.squareToScreen('d5'));
  expect(Math.abs(back.x - home.x) + Math.abs(back.y - home.y)).toBeLessThan(1);
  await page.screenshot({ path: `${SHOTS}/kampf_7_zurueck.png` });
  expect(errors).toEqual([]);
});

test('Ritter: Modus „Beide (ohne Computer)“ – Weiß und Schwarz zieht der Spieler', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/?figurensatz=ritter&brett=schnitz');
  await page.waitForSelector('body[data-ready="1"]', { timeout: 60_000 });
  await page.getByTestId('color').selectOption('beide');
  await page.waitForTimeout(800);
  // langsame GPU: ein Zug kann bei wenigen Bildern/s deutlich länger dauern
  const idle = (n) => page.waitForFunction((k) => window.chessApp.isIdle() && window.chessApp.history().length === k, n,
    { timeout: 90_000 });
  await clickSquare(page, 'e2');
  await clickSquare(page, 'e4');
  await idle(1);
  await page.waitForTimeout(1500);   // der Computer darf nicht antworten
  expect(await page.evaluate(() => window.chessApp.history())).toEqual(['e4']);
  await expect(page.getByTestId('status')).toHaveText('Schwarz ist am Zug.');
  await clickSquare(page, 'd7');
  await clickSquare(page, 'd5');
  await idle(2);
  expect(await page.evaluate(() => window.chessApp.history())).toEqual(['e4', 'd5']);
  await page.getByTestId('undo').click();
  expect(await page.evaluate(() => window.chessApp.history())).toEqual(['e4']);
  expect(errors).toEqual([]);
});

test('Ritter: Kamera frei drehbar, beim Zug zurück in die Startansicht und gesperrt', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  await page.goto('/?figurensatz=ritter&brett=schnitz');
  await page.waitForSelector('body[data-ready="1"]', { timeout: 60_000 });
  await page.getByTestId('level').selectOption('1');
  await page.waitForTimeout(1200);
  const cam = () => page.evaluate(() => window.chessApp.camera());
  const start = await cam();
  const away = (c) => Math.hypot(...c.pos.map((v, i) => v - start.pos[i]));
  expect(start.locked).toBe(false);
  // mit der Maus drehen
  await page.mouse.move(500, 450);
  await page.mouse.down();
  await page.mouse.move(700, 400, { steps: 10 });
  await page.mouse.up();
  await page.waitForTimeout(1500);
  const turned = await cam();
  expect(turned.home).toBe(false);
  expect(away(turned)).toBeGreaterThan(1);
  await clickSquare(page, 'e2');
  await clickSquare(page, 'e4');
  // sofort gesperrt, dann zurück in die Startansicht (ohne GPU langsam, daher warten statt fester Zeit)
  expect((await cam()).locked).toBe(true);
  await page.waitForFunction((p) => {
    const c = window.chessApp.camera();
    return Math.hypot(...c.pos.map((v, i) => v - p[i])) < 0.01;
  }, start.pos, { timeout: 30_000 });
  // Mausrad und Ziehen ändern während des Zugs nichts
  await page.mouse.move(500, 450);
  await page.mouse.wheel(0, -600);
  await page.mouse.down();
  await page.mouse.move(700, 400, { steps: 5 });
  await page.mouse.up();
  await page.waitForTimeout(1500);
  expect(away(await cam())).toBeLessThan(0.01);
  // nach dem Zug (und der Antwort des Computers) wieder frei
  await page.waitForFunction(() => window.chessApp.isIdle() && window.chessApp.history().length === 2, null, { timeout: 90_000 });
  expect((await cam()).locked).toBe(false);
  expect(errors).toEqual([]);
});
