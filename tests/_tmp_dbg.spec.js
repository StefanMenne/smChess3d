import { test } from '@playwright/test';
async function click(page, sq) {
  const p = await page.evaluate((s) => window.chessApp.squareToScreen(s), sq);
  console.log('click', sq, Math.round(p.x), Math.round(p.y));
  await page.mouse.click(p.x, p.y);
}
for (const delay of [0, 3000]) {
  test('dbg ' + delay, async ({ page }) => {
    page.on('console', (m) => console.log('  [page]', m.text()));
    page.on('pageerror', (e) => console.log('  [err]', e.message));
    await page.goto('/');
    await page.waitForSelector('body[data-ready="1"]', { timeout: 30_000 });
    await page.getByTestId('level').selectOption('1');
    await page.waitForTimeout(delay);
    await click(page, 'e2');
    await page.waitForTimeout(300);
    await click(page, 'e4');
    await page.waitForTimeout(4000);
    console.log(delay, await page.evaluate(() => [window.chessApp.history(), window.chessApp.isIdle(), window.chessApp.pieceAt('e4'), window.chessApp.pieceAt('e2')]),
      await page.getByTestId('status').textContent());
  });
}
