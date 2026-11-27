import { test, expect } from '@playwright/test';

// Figurensätze, Bretter und Licht. Screenshots zum Vergleichen der Optik landen in konzepte/web_shots/ (nicht im Repo).
const SHOTS = 'konzepte/web_shots';
// ohne schnelle GPU rendert Chromium die Schnitzfiguren nur mit etwa 10 Bildern/s
test.describe.configure({ timeout: 180_000 });

async function open(page, query = '') {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  await page.goto('/' + query);
  await page.waitForSelector('body[data-ready="1"]', { timeout: 60_000 });
  await page.getByTestId('level').selectOption('1');
  return errors;
}

// Zug über die Testschnittstelle per Klick auf die Felder (wie in chess.spec.js)
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

const waitIdle = (page, n) => page.waitForFunction(
  (k) => window.chessApp.isIdle() && window.chessApp.history().length === k, n, { timeout: 60_000 });

test('Standard beim ersten Start: Schnitzbrett und Schnitzfiguren', async ({ page }) => {
  const errors = await open(page);
  expect(await page.evaluate(() => window.chessApp.sets())).toEqual({ brett: 'schnitz', figuren: 'schnitz' });
  await expect(page.getByTestId('piece-set')).toHaveValue('schnitz');
  await expect(page.getByTestId('board-set')).toHaveValue('schnitz');
  expect(await page.evaluate(() => window.chessApp.pieceCount())).toBe(32);
  expect(await page.evaluate(() => window.chessApp.anim('e2'))).toBe('Idle');
  await page.screenshot({ path: `${SHOTS}/schnitz_1_start.png` });
  expect(errors).toEqual([]);
});

test('Ritter (im Aufbau): Bauern, Läufer, Damen, Könige, Türme und Springer beider Farben', async ({ page }) => {
  test.setTimeout(360_000);   // viele Züge und Nahaufnahmen
  const errors = await open(page, '?figurensatz=ritter&brett=schnitz');
  await expect(page.getByTestId('piece-set')).toHaveValue('ritter');
  expect(await page.evaluate(() => window.chessApp.pieceCount())).toBe(32);
  expect(await page.evaluate(() => window.chessApp.anim('e2'))).toBe('Idle');
  await page.screenshot({ path: `${SHOTS}/ritter_1_start.png` });
  await clickSquare(page, 'e2');
  await clickSquare(page, 'e4');
  await page.waitForTimeout(400);
  expect(await page.evaluate(() => window.chessApp.anim('e4'))).toBe('WalkInPlace');
  await page.screenshot({ path: `${SHOTS}/ritter_3_laufen.png` });
  await waitIdle(page, 2);
  expect(await page.evaluate(() => window.chessApp.anim('e4'))).toBe('Idle');
  await page.screenshot({ path: `${SHOTS}/ritter_4_ende.png` });
  // Läufer f1 nach c4 (Diagonale ist nach e4 frei)
  await page.evaluate(() => window.chessApp.newGame('rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2'));
  await clickSquare(page, 'f1');
  await clickSquare(page, 'c4');
  await page.waitForTimeout(500);
  expect(await page.evaluate(() => window.chessApp.anim('c4'))).toBe('WalkInPlace');
  await page.screenshot({ path: `${SHOTS}/ritter_5_laeufer.png` });
  await waitIdle(page, 2);
  expect(await page.evaluate(() => window.chessApp.pieceAt('c4'))).toBe('wb');
  // weißer Springer g1-f3 (geht um die Ecke)
  await page.evaluate(() => window.chessApp.newGame());
  await clickSquare(page, 'g1');
  await clickSquare(page, 'f3');
  await page.waitForTimeout(400);
  expect(await page.evaluate(() => window.chessApp.anim('f3'))).toBe('WalkInPlace');
  await waitIdle(page, 2);
  expect(await page.evaluate(() => window.chessApp.pieceAt('f3'))).toBe('wn');
  // weißer Turm: Bauer a2 weg, Turm rollt a1-a3
  await page.evaluate(() => window.chessApp.newGame('rnbqkbnr/pppppppp/8/8/8/8/1PPPPPPP/RNBQKBNR w KQkq - 0 1'));
  await clickSquare(page, 'a1');
  await clickSquare(page, 'a3');
  await page.waitForTimeout(400);
  expect(await page.evaluate(() => window.chessApp.anim('a3'))).toMatch(/Walk/);
  await page.evaluate(() => window.chessApp.setView([-1.2, 1.4, 1.6], [-3.5, 0.5, 2.5]));
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${SHOTS}/ritter_11_turm.png` });
  await waitIdle(page, 2);
  expect(await page.evaluate(() => window.chessApp.pieceAt('a3'))).toBe('wr');
  await page.evaluate(() => window.chessApp.setView([-0.6, 1.5, -0.2], [-2.8, 0.55, 2.5]));
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${SHOTS}/ritter_2_nah.png` });
  // schwarzer Läufer c8 von vorn (aus Richtung Weiß)
  await page.evaluate(() => window.chessApp.setView([-1.0, 1.4, -1.6], [-1.5, 0.75, -3.5]));
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${SHOTS}/ritter_6_schwarz.png` });
  // weiße Dame d1 von vorn (aus Richtung Schwarz)
  await page.evaluate(() => window.chessApp.setView([0.0, 1.7, 1.2], [-0.5, 0.9, 3.5]));
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${SHOTS}/ritter_7_dame.png` });
  // schwarze Dame d8 von vorn (aus Richtung Weiß)
  await page.evaluate(() => window.chessApp.setView([0.0, 1.7, -1.2], [-0.5, 0.9, -3.5]));
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${SHOTS}/ritter_8_dame_schwarz.png` });
  // weißer König e1 von vorn (aus Richtung Schwarz)
  await page.evaluate(() => window.chessApp.setView([1.6, 0.9, 1.6], [0.5, 0.6, 3.5]));
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${SHOTS}/ritter_9_koenig.png` });
  // schwarzer König e8 von vorn (aus Richtung Weiß), etwas weiter weg wegen der hohen Fahne
  await page.evaluate(() => window.chessApp.setView([0.8, 1.8, -0.4], [0.5, 1.2, -3.5]));
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${SHOTS}/ritter_10_koenig_schwarz.png` });
  // weißer Springer g1 von vorn (aus Richtung Schwarz)
  await page.evaluate(() => window.chessApp.setView([2.6, 1.6, 1.2], [2.5, 0.8, 3.5]));
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${SHOTS}/ritter_12_springer.png` });
  // schwarzer Springer g8 von vorn (Schwarz zieht der Computer, die Bewegungen sind dieselben wie beim weißen)
  await page.evaluate(() => window.chessApp.newGame());
  expect(await page.evaluate(() => window.chessApp.pieceAt('g8'))).toBe('bn');
  await page.evaluate(() => window.chessApp.setView([1.4, 1.5, -1.4], [1.9, 0.7, -3.5]));
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${SHOTS}/ritter_12_springer_schwarz.png` });
  expect(errors).toEqual([]);
});

test('Schnitzfiguren: gehen mit WalkInPlace, Springer läuft um die Ecke, Schlagen', async ({ page }) => {
  const errors = await open(page, '?figurensatz=schnitz&brett=schnitz');
  await clickSquare(page, 'e2');
  await clickSquare(page, 'e4');
  await page.waitForTimeout(300);
  expect(await page.evaluate(() => window.chessApp.anim('e4'))).toBe('WalkInPlace');
  await page.screenshot({ path: `${SHOTS}/schnitz_2_laufen.png` });
  await waitIdle(page, 2);
  expect(await page.evaluate(() => window.chessApp.anim('e4'))).toBe('Idle');
  // Schlagen: eine Stellung, in der Weiß sofort schlagen kann
  await page.evaluate(() => window.chessApp.newGame('rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2'));
  await clickSquare(page, 'e4');
  await clickSquare(page, 'd5');
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${SHOTS}/schnitz_3_schlagen.png` });
  await waitIdle(page, 2);
  expect(await page.evaluate(() => window.chessApp.history()[0])).toBe('exd5');
  expect(await page.evaluate(() => window.chessApp.pieceCount())).toBeLessThanOrEqual(31);
  await page.getByTestId('new-game').click();
  await clickSquare(page, 'g1');
  await clickSquare(page, 'f3');
  await page.waitForTimeout(300);
  expect(await page.evaluate(() => window.chessApp.anim('f3'))).toBe('WalkInPlace');
  await waitIdle(page, 2);
  expect(await page.evaluate(() => window.chessApp.pieceAt('f3'))).toBe('wn');
  expect(errors).toEqual([]);
});

test('Tierfiguren auf dem Spielzeugbrett: laden, Hase hüpft, Wechsel im Panel behält die Partie', async ({ page }) => {
  const errors = await open(page, '?brett=tiere&figurensatz=tiere');
  expect(await page.evaluate(() => window.chessApp.pieceCount())).toBe(32);
  expect(await page.evaluate(() => window.chessApp.anim('e2'))).toBe('Idle');
  await page.screenshot({ path: `${SHOTS}/tiere_1_start.png` });
  await clickSquare(page, 'e2');
  await clickSquare(page, 'e4');
  await page.waitForTimeout(200);
  expect(await page.evaluate(() => window.chessApp.anim('e4'))).toBe('Walk');
  await waitIdle(page, 2);
  const history = await page.evaluate(() => window.chessApp.history());
  // Auswahl im Panel: zurück zum Schnitzbrett, die Tierfiguren bleiben (getrennt wählbar), die Partie auch
  await page.getByTestId('board-set').selectOption('schnitz');
  await page.waitForSelector('body[data-ready="1"]', { timeout: 60_000 });
  expect(await page.evaluate(() => window.chessApp.sets())).toEqual({ brett: 'schnitz', figuren: 'tiere' });
  await expect(page.getByTestId('board-set')).toHaveValue('schnitz');
  await expect(page.getByTestId('piece-set')).toHaveValue('tiere');
  expect(await page.evaluate(() => window.chessApp.history())).toEqual(history);
  expect(await page.evaluate(() => window.chessApp.pieceAt('e4'))).toBe('wp');
  await expect(page.getByTestId('status')).toHaveText('Du bist am Zug.');
  expect(errors).toEqual([]);
});

test('Lichtregler: ändern die Helligkeit ohne Fehler und bleiben gespeichert', async ({ page }) => {
  const errors = await open(page);
  await page.locator('#moreSettings summary').click();
  await page.locator('#lightSun').fill('1.6');
  await expect(page.locator('#lightSunVal')).toHaveText('160 %');
  await page.waitForTimeout(200);
  await page.screenshot({ path: `${SHOTS}/licht_sonne160.png` });
  const variants = {
    a_sonne: { ambient: 0.5, sun: 1.3, front: 0.6 },
    b_kontrast: { ambient: 0.3, sun: 1.6, front: 0.3 },
    c_weich: { ambient: 0.8, sun: 0.9, front: 0.4 },
  };
  for (const [name, v] of Object.entries(variants)) {
    await page.evaluate((x) => window.chessApp.setLight(x), v);
    await page.waitForTimeout(200);
    await page.screenshot({ path: `${SHOTS}/licht_${name}.png` });
  }
  await page.locator('#lightSun').fill('1.2');
  await page.reload();
  await page.waitForSelector('body[data-ready="1"]', { timeout: 60_000 });
  await expect(page.locator('#lightSun')).toHaveValue('1.2');
  expect(errors).toEqual([]);
});

test('Staunton (gedrechselt): starre Figuren gleiten, der Springer springt im Bogen', async ({ page }) => {
  const errors = await open(page, '?figurensatz=staunton&brett=schnitz');
  expect(await page.evaluate(() => window.chessApp.pieceCount())).toBe(32);
  await page.screenshot({ path: `${SHOTS}/staunton_1_start.png` });
  await clickSquare(page, 'g1');
  await clickSquare(page, 'f3');
  // mitten im Sprung: über dem Brett
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${SHOTS}/staunton_2_sprung.png` });
  await waitIdle(page, 2);
  expect(await page.evaluate(() => window.chessApp.pieceAt('f3'))).toBe('wn');
  await clickSquare(page, 'e2');
  await clickSquare(page, 'e4');
  await waitIdle(page, 4);
  expect(await page.evaluate(() => window.chessApp.pieceAt('e4'))).toBe('wp');
  await page.screenshot({ path: `${SHOTS}/staunton_3_ende.png` });
  expect(errors).toEqual([]);
});

test('Staunton: Material je Farbe wählbar, bleibt gespeichert; bei anderen Sätzen ausgeblendet', async ({ page }) => {
  const errors = await open(page, '?figurensatz=staunton&brett=schnitz');
  await page.locator('#moreSettings summary').click();
  await expect(page.getByTestId('material-white')).toBeVisible();
  const pairs = [['holz', 'holz'], ['ahorn', 'nussbaum'], ['elfenbein', 'palisander'], ['porzellan', 'lack'], ['silber', 'gold'], ['glas', 'rauchglas']];
  for (const [w, b] of pairs) {
    await page.getByTestId('material-white').selectOption(w);
    await page.getByTestId('material-black').selectOption(b);
    await page.evaluate(() => window.chessApp.setView([3.2, 3.0, 5.2], [0, 0.5, 0.6]));
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SHOTS}/material_${w}_${b}.png`, clip: { x: 0, y: 0, width: 1088, height: 900 } });
  }
  await page.reload();
  await page.waitForSelector('body[data-ready="1"]', { timeout: 60_000 });
  await expect(page.getByTestId('material-white')).toHaveValue('glas');
  await expect(page.getByTestId('material-black')).toHaveValue('rauchglas');
  await page.goto('/?figurensatz=schnitz&brett=schnitz');
  await page.waitForSelector('body[data-ready="1"]', { timeout: 60_000 });
  await expect(page.locator('#pieceMaterials')).toBeHidden();
  expect(errors).toEqual([]);
});
