#!/usr/bin/env node
/**
 * Connect Four, played from the profile README via GitHub Issues.
 *
 * A visitor clicks a column arrow, which opens a pre-filled issue titled
 * `c4|drop|<0-6>` (or `c4|reset`). The workflow runs this script, which drops
 * the visitor's disc, lets the AI answer, and rewrites the board block in
 * README.md between the C4 markers.
 *
 * Usage: node game/c4.js "<issue title>" "<actor login>"
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const STATE_FILE = path.join(__dirname, 'state.json');
const README = path.join(ROOT, 'README.md');

const REPO = process.env.GITHUB_REPOSITORY || 'gabbygab18/gabbygab18';

const COLS = 7;
const ROWS = 6;
const HUMAN = 'R';
const AI = 'Y';
const EMPTY = '.';
const DEPTH = 6;

const at = (board, r, c) => board[r * COLS + c];
const set = (board, r, c, v) => { board[r * COLS + c] = v; };

/** Every 4-in-a-row window on the board, precomputed once. */
const WINDOWS = (() => {
  const out = [];
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      if (c + 3 < COLS) out.push([[r, c], [r, c + 1], [r, c + 2], [r, c + 3]]);
      if (r + 3 < ROWS) out.push([[r, c], [r + 1, c], [r + 2, c], [r + 3, c]]);
      if (r + 3 < ROWS && c + 3 < COLS) out.push([[r, c], [r + 1, c + 1], [r + 2, c + 2], [r + 3, c + 3]]);
      if (r + 3 < ROWS && c - 3 >= 0) out.push([[r, c], [r + 1, c - 1], [r + 2, c - 2], [r + 3, c - 3]]);
    }
  }
  return out;
})();

function newGame(scores) {
  return {
    board: Array(COLS * ROWS).fill(EMPTY),
    status: 'playing',
    lastDrop: null,
    scores: scores || { wins: 0, losses: 0, draws: 0 },
  };
}

function loadState() {
  try {
    const s = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    if (Array.isArray(s.board) && s.board.length === COLS * ROWS) return s;
  } catch (_) { /* fall through to a fresh game */ }
  return newGame();
}

function winner(board) {
  for (const w of WINDOWS) {
    const first = at(board, w[0][0], w[0][1]);
    if (first === EMPTY) continue;
    if (w.every(([r, c]) => at(board, r, c) === first)) {
      return { mark: first, cells: w.map(([r, c]) => r * COLS + c) };
    }
  }
  return null;
}

const openColumns = (board) => {
  const out = [];
  for (let c = 0; c < COLS; c++) if (at(board, 0, c) === EMPTY) out.push(c);
  return out;
};

/** Lowest empty row in a column, or -1 when the column is full. */
function landingRow(board, col) {
  for (let r = ROWS - 1; r >= 0; r--) if (at(board, r, col) === EMPTY) return r;
  return -1;
}

function drop(board, col, mark) {
  const r = landingRow(board, col);
  if (r === -1) return -1;
  set(board, r, col, mark);
  return r * COLS + col;
}

const isFull = (board) => openColumns(board).length === 0;

/** Positional score for one 4-window, from the AI's point of view. */
function scoreWindow(cells, board) {
  let ai = 0, human = 0, empty = 0;
  for (const [r, c] of cells) {
    const v = at(board, r, c);
    if (v === AI) ai++;
    else if (v === HUMAN) human++;
    else empty++;
  }
  if (ai && human) return 0;
  if (ai === 3 && empty === 1) return 50;
  if (ai === 2 && empty === 2) return 8;
  if (human === 3 && empty === 1) return -60; // block harder than we build
  if (human === 2 && empty === 2) return -8;
  return 0;
}

function evaluate(board) {
  let score = 0;
  for (const w of WINDOWS) score += scoreWindow(w, board);
  // Centre control is worth real tempo in Connect Four.
  for (let r = 0; r < ROWS; r++) {
    const v = at(board, r, 3);
    if (v === AI) score += 6;
    else if (v === HUMAN) score -= 6;
  }
  return score;
}

/** Search centre columns first so alpha-beta prunes more. */
const ORDER = [3, 2, 4, 1, 5, 0, 6];

function negamax(board, depth, alpha, beta, mark) {
  const win = winner(board);
  if (win) {
    const sign = win.mark === AI ? 1 : -1;
    return { score: sign * (100000 + depth), col: null };
  }
  if (isFull(board)) return { score: 0, col: null };
  if (depth === 0) return { score: evaluate(board), col: null };

  const maximizing = mark === AI;
  let best = { score: maximizing ? -Infinity : Infinity, col: null };

  for (const c of ORDER) {
    if (at(board, 0, c) !== EMPTY) continue;
    const idx = drop(board, c, mark);
    const { score } = negamax(board, depth - 1, alpha, beta, mark === AI ? HUMAN : AI);
    board[idx] = EMPTY;

    if (maximizing) {
      if (score > best.score) best = { score, col: c };
      alpha = Math.max(alpha, score);
    } else {
      if (score < best.score) best = { score, col: c };
      beta = Math.min(beta, score);
    }
    if (alpha >= beta) break;
  }
  return best;
}

function aiMove(board) {
  const open = openColumns(board);
  if (!open.length) return -1;

  // Take an immediate win, and block an immediate loss, without searching.
  for (const [mark] of [[AI], [HUMAN]]) {
    for (const c of open) {
      const probe = board.slice();
      drop(probe, c, mark);
      if (winner(probe)) return c;
    }
  }

  const best = negamax(board.slice(), DEPTH, -Infinity, Infinity, AI);
  return best.col !== null && open.includes(best.col) ? best.col : open[0];
}

function applyTitle(state, title) {
  const parts = String(title).trim().toLowerCase().split('|').map((p) => p.trim());
  if (parts[0] !== 'c4') return { ok: false, reason: 'not a game issue' };

  if (parts[1] === 'reset') {
    Object.assign(state, newGame(state.scores));
    return { ok: true, reason: 'new game started' };
  }

  if (parts[1] !== 'drop') return { ok: false, reason: 'unknown command' };

  const col = Number(parts[2]);
  if (!Number.isInteger(col) || col < 0 || col >= COLS) {
    return { ok: false, reason: `column must be 0-${COLS - 1}` };
  }

  // A finished board auto-restarts so the clicked column still counts as move one.
  if (state.status !== 'playing') Object.assign(state, newGame(state.scores));
  if (at(state.board, 0, col) !== EMPTY) return { ok: false, reason: 'that column is full' };

  state.lastDrop = drop(state.board, col, HUMAN);

  if (winner(state.board)) {
    state.status = HUMAN;
    state.scores.wins += 1;
    return { ok: true, reason: 'you win' };
  }
  if (isFull(state.board)) {
    state.status = 'draw';
    state.scores.draws += 1;
    return { ok: true, reason: 'draw' };
  }

  state.lastDrop = drop(state.board, aiMove(state.board), AI);

  if (winner(state.board)) {
    state.status = AI;
    state.scores.losses += 1;
    return { ok: true, reason: 'AI wins' };
  }
  if (isFull(state.board)) {
    state.status = 'draw';
    state.scores.draws += 1;
    return { ok: true, reason: 'draw' };
  }

  return { ok: true, reason: 'your turn' };
}

const icon = (name, color, size) =>
  `https://api.iconify.design/${name}.svg?color=%23${color}&width=${size}&height=${size}`;

const DISC = {
  [HUMAN]: icon('bxs:circle', 'f778ba', 34),
  [AI]: icon('bxs:circle', '58a6ff', 34),
  [EMPTY]: icon('bx:circle', '21262d', 34),
  win: icon('bxs:star', 'f0d264', 34),
  arrow: icon('bxs:down-arrow', '3fb950', 22),
  arrowOff: icon('bx:down-arrow', '30363d', 22),
};

const issueUrl = (title) =>
  `https://github.com/${REPO}/issues/new?title=${encodeURIComponent(title)}` +
  `&body=${encodeURIComponent('Leave this as-is and press Create. The board updates in about a minute.')}`;

function renderBoard(state) {
  const over = state.status !== 'playing';
  const win = winner(state.board);
  const highlight = new Set(win ? win.cells : []);

  const head = [];
  for (let c = 0; c < COLS; c++) {
    const playable = !over && at(state.board, 0, c) === EMPTY;
    head.push(
      playable
        ? `<a href="${issueUrl(`c4|drop|${c}`)}" title="drop in column ${c + 1}">` +
          `<img src="${DISC.arrow}" width="22" alt="drop here" /></a>`
        : `<img src="${DISC.arrowOff}" width="22" alt="" />`
    );
  }

  const rows = [`  <tr>\n${head.map((h) => `    <td align="center" height="34">${h}</td>`).join('\n')}\n  </tr>`];

  for (let r = 0; r < ROWS; r++) {
    const cells = [];
    for (let c = 0; c < COLS; c++) {
      const i = r * COLS + c;
      const v = state.board[i];
      const src = highlight.has(i) ? DISC.win : DISC[v];
      const label = v === EMPTY ? 'empty' : v === HUMAN ? 'you' : 'ai';
      cells.push(`<img src="${src}" width="34" alt="${label}" />`);
    }
    rows.push(
      `  <tr>\n${cells.map((c) => `    <td align="center" height="46" width="46">${c}</td>`).join('\n')}\n  </tr>`
    );
  }

  const status = {
    playing: 'your move — click an arrow to drop a disc',
    [HUMAN]: 'you beat it. that is not easy.',
    [AI]: 'AI connects four. run it back?',
    draw: 'board full — draw.',
  }[state.status];

  const s = state.scores;

  return [
    '<div align="center">',
    '',
    `<table>\n${rows.join('\n')}\n</table>`,
    '',
    `<img src="${DISC[HUMAN]}" width="13" /> you &nbsp;&nbsp; <img src="${DISC[AI]}" width="13" /> ai`,
    '',
    `**${status}**`,
    '',
    `<img src="${icon('bx:trophy', '3fb950', 16)}" width="14" /> you **${s.wins}** ` +
      `&nbsp;·&nbsp; <img src="${icon('bx:bot', 'f778ba', 16)}" width="14" /> ai **${s.losses}** ` +
      `&nbsp;·&nbsp; <img src="${icon('bx:minus', '8b949e', 16)}" width="14" /> draws **${s.draws}**`,
    '',
    `<a href="${issueUrl('c4|reset')}"><img src="https://img.shields.io/badge/new%20game-238636?style=for-the-badge&logo=github&logoColor=white" alt="new game" /></a>`,
    '',
    '<sub>clicking an arrow opens a pre-filled issue — just press <b>Create</b>. ' +
      'a workflow plays the reply and updates this board within a minute.</sub>',
    '',
    '</div>',
  ].join('\n');
}

function writeReadme(state) {
  const md = fs.readFileSync(README, 'utf8');
  const start = '<!--C4_START-->';
  const end = '<!--C4_END-->';
  const a = md.indexOf(start);
  const b = md.indexOf(end);
  if (a === -1 || b === -1) throw new Error('C4 markers missing from README.md');
  fs.writeFileSync(README, md.slice(0, a + start.length) + '\n' + renderBoard(state) + '\n' + md.slice(b));
}

function main() {
  const title = process.argv[2] || '';
  const actor = process.argv[3] || 'someone';
  const state = loadState();
  const result = applyTitle(state, title);

  if (result.ok) {
    state.lastActor = actor;
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2) + '\n');
    writeReadme(state);
  }

  // Consumed by the workflow for the issue reply and the commit message.
  fs.writeFileSync(
    path.join(__dirname, 'result.txt'),
    `${result.ok ? 'ok' : 'rejected'}: ${result.reason}\n`
  );
  console.log(`${result.ok ? 'ok' : 'rejected'}: ${result.reason}`);
}

main();
