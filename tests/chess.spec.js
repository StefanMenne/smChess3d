import { test, expect } from '@playwright/test';

// Die Feldmitte kann hinter der Figur davor liegen (z.B. d2 hinter der Dame) -> eine Stelle über dem Feld
// suchen, die die App selbst diesem Feld zuordnet, und dort klicken
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

async function move(page, from, to) {
  await clickSquare(page, from);
  await clickSquare(page, to);
}

async function waitIdle(page, plies) {
  await page.waitForFunction(
    (n) => window.chessApp.isIdle() && (n == null || window.chessApp.history().length === n),
    plies,
    { timeout: 30_000 },
  );
}

test.beforeEach(async ({ page }) => {
  page.on('pageerror', (e) => { throw e; });
  await page.goto('/');
  await page.waitForSelector('body[data-ready="1"]', { timeout: 30_000 });
  await page.getByTestId('level').selectOption('1');
});

test('Startstellung wird mit 32 Figuren geladen', async ({ page }) => {
  expect(await page.evaluate(() => window.chessApp.pieceCount())).toBe(32);
  await expect(page.getByTestId('status')).toHaveText('Du bist am Zug.');
  expect(await page.evaluate(() => window.chessApp.pieceAt('e1'))).toBe('wk');
  expect(await page.evaluate(() => window.chessApp.pieceAt('d8'))).toBe('bq');
});

test('Spielerzug per Klick, Computer antwortet', async ({ page }) => {
  await move(page, 'e2', 'e4');
  await waitIdle(page, 2);
  const history = await page.evaluate(() => window.chessApp.history());
  expect(history[0]).toBe('e4');
  expect(await page.evaluate(() => window.chessApp.pieceAt('e4'))).toBe('wp');
  await expect(page.getByTestId('moves').locator('li')).toHaveCount(1);
  await expect(page.getByTestId('status')).toHaveText('Du bist am Zug.');
});

test('Unerlaubter Zug wird ignoriert', async ({ page }) => {
  await move(page, 'e2', 'e5');
  await page.waitForTimeout(300);
  expect(await page.evaluate(() => window.chessApp.history())).toEqual([]);
  expect(await page.evaluate(() => window.chessApp.pieceAt('e2'))).toBe('wp');
});

test('Rochade bewegt König und Turm', async ({ page }) => {
  await page.evaluate(() => window.chessApp.newGame('r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1'));
  await move(page, 'e1', 'g1');
  await waitIdle(page, 2);
  expect(await page.evaluate(() => window.chessApp.pieceAt('g1'))).toBe('wk');
  expect(await page.evaluate(() => window.chessApp.pieceAt('f1'))).toBe('wr');
  expect(await page.evaluate(() => window.chessApp.pieceAt('h1'))).toBeNull();
});

test('En passant entfernt den geschlagenen Bauern', async ({ page }) => {
  await page.evaluate(() => window.chessApp.newGame('rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3'));
  await move(page, 'e5', 'd6');
  await waitIdle(page, 2);
  expect(await page.evaluate(() => window.chessApp.history()[0])).toBe('exd6');
  expect(await page.evaluate(() => window.chessApp.pieceCount())).toBeLessThanOrEqual(31);
  expect(await page.evaluate(() => window.chessApp.fen())).not.toContain('3pP3');
});

test('Bauernumwandlung mit Auswahl', async ({ page }) => {
  await page.evaluate(() => window.chessApp.newGame('7k/P6p/8/8/8/8/8/K7 w - - 0 1'));
  await move(page, 'a7', 'a8');
  await page.getByRole('button', { name: 'Springer' }).click();
  await waitIdle(page, 2);
  expect(await page.evaluate(() => window.chessApp.history()[0])).toBe('a8=N');
  expect(await page.evaluate(() => window.chessApp.pieceAt('a8'))).toBe('wn');
});

test('Schachmatt wird erkannt', async ({ page }) => {
  await page.evaluate(() => window.chessApp.newGame('k7/7Q/1K6/8/8/8/8/8 w - - 0 1'));
  await move(page, 'h7', 'b7');
  await waitIdle(page, 1);
  await expect(page.getByTestId('status')).toHaveText('Schachmatt – du gewinnst!');
});

test('Zug zurücknehmen stellt die Startstellung wieder her', async ({ page }) => {
  await move(page, 'd2', 'd4');
  await waitIdle(page, 2);
  await page.getByTestId('undo').click();
  await waitIdle(page, 0);
  expect(await page.evaluate(() => window.chessApp.pieceCount())).toBe(32);
  expect(await page.evaluate(() => window.chessApp.pieceAt('d2'))).toBe('wp');
});

test('Als Schwarz beginnt der Computer', async ({ page }) => {
  await page.getByTestId('color').selectOption('b');
  await waitIdle(page, 1);
  expect(await page.evaluate(() => window.chessApp.playerColor())).toBe('b');
  await expect(page.getByTestId('status')).toHaveText('Du bist am Zug.');
});

test('Computer findet ein Matt in eins', async ({ page }) => {
  await page.getByTestId('level').selectOption('3');
  // Narrenmatt: Weiß hat f3 und g4 gezogen, Schwarz (Computer) ist am Zug
  await page.evaluate(() => window.chessApp.newGame('rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq g3 0 2'));
  await waitIdle(page, 1);
  expect(await page.evaluate(() => window.chessApp.history()[0])).toBe('Qh4#');
  await expect(page.getByTestId('status')).toHaveText('Schachmatt – der Computer gewinnt.');
});

test('Einstellungen: Toon-Rendering lässt sich einschalten und bleibt gespeichert', async ({ page }) => {
  expect(await page.evaluate(() => window.chessApp.toon())).toBe(false);
  await page.getByTestId('settings').click();
  await page.getByTestId('toon').check();
  await page.getByTestId('settings-close').click();
  expect(await page.evaluate(() => window.chessApp.toon())).toBe(true);
  await page.reload();
  await page.waitForSelector('body[data-ready="1"]', { timeout: 30_000 });
  expect(await page.evaluate(() => window.chessApp.toon())).toBe(true);
  await expect(page.getByTestId('toon')).toBeChecked();
});

test('Einstellungen: Rendering-Infos zeigen die FPS an', async ({ page }) => {
  await expect(page.getByTestId('stats')).toBeHidden();
  await page.getByTestId('settings').click();
  await page.getByTestId('render-info').check();
  await page.getByTestId('settings-close').click();
  await expect(page.getByTestId('stats')).toHaveText(/^\d+ FPS$/);
  await page.reload();
  await page.waitForSelector('body[data-ready="1"]', { timeout: 30_000 });
  await expect(page.getByTestId('stats')).toBeVisible();
});

test('Info-Dialog zeigt die Lizenztexte', async ({ page }) => {
  await page.getByTestId('info').click();
  const dlg = page.getByTestId('info-dialog');
  await expect(dlg).toBeVisible();
  const three = dlg.locator('details[data-license="licenses/three.js.txt"]');
  await three.locator('summary').click();
  await expect(three.locator('pre')).toContainText('Permission is hereby granted');
  for (const f of await dlg.locator('details[data-license]').evaluateAll((ds) => ds.map((d) => d.dataset.license))) {
    expect((await page.request.get(f)).ok(), f).toBe(true);
  }
  await page.getByTestId('info-close').click();
  await expect(dlg).toBeHidden();
});
