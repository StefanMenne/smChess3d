import { test, expect } from '@playwright/test';

async function clickSquare(page, sq) {
  const { x, y } = await page.evaluate((s) => window.chessApp.squareToScreen(s), sq);
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
