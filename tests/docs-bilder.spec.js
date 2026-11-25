import { test } from '@playwright/test';

// Bilder für die README in docs/ (nur mit DOCS=1): npx playwright test docs-bilder  (DOCS=1 davor setzen)
// Roh-Screenshots in doppelter Auflösung landen in konzepte/docs_roh/, verkleinert werden sie danach mit
// tools/docs_bilder.py
test.skip(!process.env.DOCS, 'nur mit DOCS=1');
test.describe.configure({ timeout: 300_000 });
test.use({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 2 });

const RAW = 'konzepte/docs_roh';

async function open(page, query) {
  await page.goto('/' + query);
  await page.waitForSelector('body[data-ready="1"]', { timeout: 120_000 });
}

// Partie bis zu einer Stellung im Mittelspiel (Italienische Partie), Weiß zieht c3 per Klick, der Computer antwortet
async function midgame(page) {
  await page.evaluate(() => window.chessApp.newGame(undefined, '1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5'));
  await page.evaluate(async () => {
    const click = (sq) => {
      for (const h of [0.3, 0.6, 0, 0.9]) {
        const p = window.chessApp.squareToScreen(sq, h);
        if (window.chessApp.squareAtScreen(p.x, p.y) === sq) return p;
      }
      return window.chessApp.squareToScreen(sq);
    };
    window.__clicks = [click('c2'), click('c3')];
  });
  for (const p of await page.evaluate(() => window.__clicks)) await page.mouse.click(p.x, p.y);
  await page.waitForFunction(() => window.chessApp.isIdle() && window.chessApp.history().length === 8, null, { timeout: 120_000 });
  await page.waitForTimeout(1500);
}

const hidePanel = (page) => page.addStyleTag({ content: '#panel { display: none } #scene { inset: 0 !important }' })
  .then(() => page.evaluate(() => window.dispatchEvent(new Event('resize'))));

test('Schnitzfiguren im Spiel', async ({ page }) => {
  await open(page, '?figurensatz=schnitz&brett=schnitz');
  await midgame(page);
  await page.screenshot({ path: `${RAW}/schnitzfiguren.png` });
});

test('Schnitzfiguren Nahaufnahme', async ({ page }) => {
  await open(page, '?figurensatz=schnitz&brett=schnitz');
  await hidePanel(page);
  await midgame(page);
  await page.evaluate(() => window.chessApp.setView([3.0, 3.3, 6.4], [-0.5, 0.45, 0.7]));
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${RAW}/nahaufnahme.png` });
});

test('Staunton Nahaufnahme', async ({ page }) => {
  await open(page, '?figurensatz=staunton&brett=schnitz');
  await hidePanel(page);
  await midgame(page);
  await page.evaluate(() => window.chessApp.setView([3.0, 3.3, 6.4], [-0.5, 0.45, 0.7]));
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${RAW}/staunton.png` });
});

test('Tierfiguren im Spiel', async ({ page }) => {
  await open(page, '?figurensatz=tiere&brett=tiere');
  await midgame(page);
  await page.screenshot({ path: `${RAW}/tierfiguren.png` });
});
