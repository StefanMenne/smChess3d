// Computer-Gegner: Alpha-Beta-Suche mit iterativer Vertiefung,
// Ruhesuche (Schlagzüge) und Figuren-Feld-Tabellen.
import { Chess } from '/vendor/chess.js';

const VALUE = { p: 100, n: 320, b: 330, r: 500, q: 900, k: 0 };

// Tabellen aus Sicht von Weiß, Index 0 = a8 ... 63 = h1
const PST = {
  p: [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
  ],
  n: [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
  ],
  b: [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
  ],
  r: [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
  ],
  q: [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
  ],
  k: [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
  ],
  kEnd: [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
  ],
};

const MATE = 100000;

class Timeout extends Error {}

// Bewertung aus Sicht der Seite am Zug
function evaluate(game) {
  const board = game.board();
  let score = 0;
  let nonPawn = 0;
  for (const row of board) for (const sq of row) if (sq && sq.type !== 'p' && sq.type !== 'k') nonPawn += VALUE[sq.type];
  const endgame = nonPawn <= 1300;
  for (let r = 0; r < 8; r++) {
    for (let f = 0; f < 8; f++) {
      const sq = board[r][f];
      if (!sq) continue;
      const idx = sq.color === 'w' ? r * 8 + f : (7 - r) * 8 + f;
      const table = sq.type === 'k' && endgame ? PST.kEnd : PST[sq.type];
      const v = VALUE[sq.type] + table[idx];
      score += sq.color === 'w' ? v : -v;
    }
  }
  return game.turn() === 'w' ? score : -score;
}

function orderMoves(moves, pvMove) {
  const score = (m) => {
    if (pvMove && m.san === pvMove) return 1e6;
    let s = 0;
    if (m.captured) s += 10 * VALUE[m.captured] - VALUE[m.piece] + 1000;
    if (m.promotion) s += VALUE[m.promotion] + 900;
    if (m.san.includes('+')) s += 50;
    return s;
  };
  return moves.map((m) => [score(m), m]).sort((a, b) => b[0] - a[0]).map((x) => x[1]);
}

function search(game, ctx, rootSide) {
  let nodes = 0;
  const check = () => {
    if ((++nodes & 255) === 0 && performance.now() > ctx.deadline) throw new Timeout();
  };

  function quiesce(alpha, beta, qdepth) {
    check();
    const stand = evaluate(game);
    if (stand >= beta) return beta;
    if (stand > alpha) alpha = stand;
    if (qdepth <= 0) return alpha;
    const captures = orderMoves(game.moves({ verbose: true }).filter((m) => m.captured || m.promotion));
    for (const m of captures) {
      game.move(m);
      const s = -quiesce(-beta, -alpha, qdepth - 1);
      game.undo();
      if (s >= beta) return beta;
      if (s > alpha) alpha = s;
    }
    return alpha;
  }

  function negamax(depth, alpha, beta, ply) {
    check();
    if (game.isCheckmate()) return -MATE + ply;
    if (game.isDraw()) return 0;
    if (depth === 0) return quiesce(alpha, beta, 4);
    const moves = orderMoves(game.moves({ verbose: true }));
    let best = -Infinity;
    for (const m of moves) {
      game.move(m);
      const s = -negamax(depth - 1, -beta, -alpha, ply + 1);
      game.undo();
      if (s > best) best = s;
      if (s > alpha) alpha = s;
      if (alpha >= beta) break;
    }
    return best;
  }

  return { negamax, nodes: () => nodes };
}

function chooseMove(fen, level) {
  const game = new Chess(fen);
  const moves = game.moves({ verbose: true });
  if (moves.length === 0) return null;

  const cfg = {
    1: { maxDepth: 1, time: 300, noise: 120 },
    2: { maxDepth: 2, time: 1000, noise: 30 },
    3: { maxDepth: 3, time: 2500, noise: 8 },
    4: { maxDepth: 5, time: 5000, noise: 0 },
  }[level] || { maxDepth: 3, time: 2500, noise: 8 };

  const ctx = { deadline: performance.now() + cfg.time };
  const s = search(game, ctx);
  let bestSan = moves[0].san;
  let pv = null;

  for (let depth = 1; depth <= cfg.maxDepth; depth++) {
    try {
      let alpha = -Infinity;
      let iterBest = null;
      const scored = [];
      for (const m of orderMoves(moves, pv)) {
        game.move(m);
        // Volles Fenster bei Zufall, damit alle Züge vergleichbar bewertet werden
        const score = -s.negamax(depth - 1, -Infinity, cfg.noise ? Infinity : -alpha, 1);
        game.undo();
        scored.push([score + (Math.random() * 2 - 1) * cfg.noise, m.san]);
        if (score > alpha) { alpha = score; iterBest = m.san; }
      }
      scored.sort((a, b) => b[0] - a[0]);
      bestSan = cfg.noise ? scored[0][1] : iterBest;
      pv = iterBest;
      if (alpha >= MATE - 100) break; // Matt gefunden
    } catch (e) {
      if (!(e instanceof Timeout)) throw e;
      while (game.history().length) game.undo();
      break;
    }
  }
  const chosen = moves.find((m) => m.san === bestSan);
  return { from: chosen.from, to: chosen.to, promotion: chosen.promotion };
}

self.onmessage = (e) => {
  const { id, fen, level } = e.data;
  const move = chooseMove(fen, level);
  self.postMessage({ id, move });
};
