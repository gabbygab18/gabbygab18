#!/usr/bin/env node
/**
 * Tic-tac-toe played from the profile README via GitHub Issues.
 *
 * A visitor clicks a cell link, which opens a pre-filled issue titled
 * `ttt|move|<0-8>` (or `ttt|reset`). The workflow runs this script, which
 * applies the move, lets the AI answer, and rewrites the board block in
 * README.md between the TTT markers.
 *
 * Usage: node game/ttt.js "<issue title>" "<actor login>"
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const STATE_FILE = path.join(__dirname, 'state.json');
const README = path.join(ROOT, 'README.md');

const REPO = process.env.GITHUB_REPOSITORY || 'gabbygab18/gabbygab18';
const HUMAN = 'X';
const AI = 'O';

const LINES = [
  [0, 1, 2], [3, 4, 5], [6, 7, 8],
  [0, 3, 6], [1, 4, 7], [2, 5, 8],
  [0, 4, 8], [2, 4, 6],
];

const icon = (name, color, size) =>
  `https://api.iconify.design/${name}.svg?color=%23${color}&width=${size}&height=${size}`;

const ICONS = {
  X: icon('bx:x', 'f778ba', 44),
  O: icon('bx:circle', '58a6ff', 38),
  empty: icon('bx:plus', '30363d', 30),
};

function newGame(scores) {
  return {
    board: Array(9).fill('.'),
    turn: HUMAN,
    status: 'playing',
    lastMove: null,
    lastPlayer: null,
    scores: scores || { wins: 0, losses: 0, draws: 0 },
  };
}

function loadState() {
  try {
    const s = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    if (Array.isArray(s.board) && s.board.length === 9) return s;
  } catch (_) { /* fall through to a fresh game */ }
  return newGame();
}

function winner(board) {
  for (const [a, b, c] of LINES) {
    if (board[a] !== '.' && board[a] === board[b] && board[b] === board[c]) {
      return { mark: board[a], line: [a, b, c] };
    }
  }
  return null;
}

const free = (board) => board.reduce((acc, v, i) => (v === '.' ? acc.concat(i) : acc), []);

/** Minimax with depth preference, so the AI wins fast and stalls a loss. */
function minimax(board, mark) {
  const win = winner(board);
  if (win) return { score: win.mark === AI ? 10 : -10, move: null };
  const open = free(board);
  if (!open.length) return { score: 0, move: null };

  let best = null;
  for (const i of open) {
    board[i] = mark;
    const { score } = minimax(board, mark === AI ? HUMAN : AI);
    board[i] = '.';
    const adjusted = score > 0 ? score - 1 : score < 0 ? score + 1 : 0;
    if (!best || (mark === AI ? adjusted > best.score : adjusted < best.score)) {
      best = { score: adjusted, move: i };
    }
  }
  return best;
}

function aiMove(board) {
  const open = free(board);
  // Opening book. Minimax alone would always pick the same reply, so the first
  // move is chosen from the set of optimal answers to keep games varied:
  // if X took the centre, any corner draws; otherwise the centre is forced.
  if (open.length === 8) {
    const good = board[4] === '.' ? [4] : [0, 2, 6, 8].filter((i) => board[i] === '.');
    return good[Math.floor(Math.random() * good.length)];
  }
  return minimax(board.slice(), AI).move;
}

function applyTitle(state, title) {
  const parts = String(title).trim().toLowerCase().split('|').map((p) => p.trim());
  if (parts[0] !== 'ttt') return { ok: false, reason: 'not a game issue' };

  if (parts[1] === 'reset') {
    Object.assign(state, newGame(state.scores));
    return { ok: true, reason: 'new game started' };
  }

  if (parts[1] !== 'move') return { ok: false, reason: 'unknown command' };

  const cell = Number(parts[2]);
  if (!Number.isInteger(cell) || cell < 0 || cell > 8) {
    return { ok: false, reason: 'cell must be 0-8' };
  }

  // A finished board auto-restarts so the clicked cell still counts as move one.
  if (state.status !== 'playing') Object.assign(state, newGame(state.scores));
  if (state.board[cell] !== '.') return { ok: false, reason: 'that square is taken' };

  state.board[cell] = HUMAN;
  state.lastMove = cell;
  state.lastPlayer = HUMAN;

  let win = winner(state.board);
  if (win) {
    state.status = HUMAN;
    state.scores.wins += 1;
    return { ok: true, reason: 'you win' };
  }
  if (!free(state.board).length) {
    state.status = 'draw';
    state.scores.draws += 1;
    return { ok: true, reason: 'draw' };
  }

  const reply = aiMove(state.board);
  state.board[reply] = AI;
  state.lastMove = reply;
  state.lastPlayer = AI;

  win = winner(state.board);
  if (win) {
    state.status = AI;
    state.scores.losses += 1;
    return { ok: true, reason: 'AI wins' };
  }
  if (!free(state.board).length) {
    state.status = 'draw';
    state.scores.draws += 1;
    return { ok: true, reason: 'draw' };
  }

  state.turn = HUMAN;
  return { ok: true, reason: 'your turn' };
}

const issueUrl = (title) =>
  `https://github.com/${REPO}/issues/new?title=${encodeURIComponent(title)}` +
  `&body=${encodeURIComponent('Leave this as-is and press Create. The board updates in about a minute.')}`;

function renderBoard(state) {
  const over = state.status !== 'playing';
  const win = winner(state.board);
  const highlight = new Set(win ? win.line : []);

  const rows = [];
  for (let r = 0; r < 3; r++) {
    const cells = [];
    for (let c = 0; c < 3; c++) {
      const i = r * 3 + c;
      const mark = state.board[i];
      if (mark === '.') {
        cells.push(
          over
            ? `<img src="${ICONS.empty}" width="30" alt="empty" />`
            : `<a href="${issueUrl(`ttt|move|${i}`)}" title="play square ${i}">` +
              `<img src="${ICONS.empty}" width="30" alt="play here" /></a>`
        );
      } else {
        const glow = highlight.has(i)
          ? ` <img src="${icon('bxs:star', '3fb950', 12)}" width="10" alt="" />`
          : '';
        cells.push(
          `<img src="${ICONS[mark]}" width="${mark === 'X' ? 44 : 38}" alt="${mark}" />${glow}`
        );
      }
    }
    rows.push(
      `  <tr>\n${cells.map((c) => `    <td align="center" height="72" width="72">${c}</td>`).join('\n')}\n  </tr>`
    );
  }

  const status = {
    playing: 'your move — click any empty square',
    [HUMAN]: 'you win. genuinely well played.',
    [AI]: 'AI takes it. run it back?',
    draw: 'draw. the only honest result.',
  }[state.status];

  const s = state.scores;

  return [
    '<div align="center">',
    '',
    `<table>\n${rows.join('\n')}\n</table>`,
    '',
    `**${status}**`,
    '',
    `<img src="${icon('bx:trophy', '3fb950', 16)}" width="14" /> you **${s.wins}** ` +
      `&nbsp;·&nbsp; <img src="${icon('bx:bot', 'f778ba', 16)}" width="14" /> ai **${s.losses}** ` +
      `&nbsp;·&nbsp; <img src="${icon('bx:minus', '8b949e', 16)}" width="14" /> draws **${s.draws}**`,
    '',
    `<a href="${issueUrl('ttt|reset')}"><img src="https://img.shields.io/badge/new%20game-238636?style=for-the-badge&logo=github&logoColor=white" alt="new game" /></a>`,
    '',
    '<sub>clicking a square opens a pre-filled issue — just press <b>Create</b>. ' +
      'a workflow plays the reply and updates this board within a minute.</sub>',
    '',
    '</div>',
  ].join('\n');
}

function writeReadme(state) {
  const md = fs.readFileSync(README, 'utf8');
  const start = '<!--TTT_START-->';
  const end = '<!--TTT_END-->';
  const a = md.indexOf(start);
  const b = md.indexOf(end);
  if (a === -1 || b === -1) throw new Error('TTT markers missing from README.md');
  const next = md.slice(0, a + start.length) + '\n' + renderBoard(state) + '\n' + md.slice(b);
  fs.writeFileSync(README, next);
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
