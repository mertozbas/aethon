/**
 * AETHON Pixel Office — Default Office Layout
 *
 * Creates the tile map and places furniture for a cozy dev office.
 * 24 columns × 16 rows grid.
 * 6 desk workstations with seats for agents.
 */

import { createTileMap, TileType } from './tileMap.js';

const COLS = 24;
const ROWS = 16;

/**
 * Build the default office layout.
 * @returns {{ tileMap, furniture, seats, blockedTiles, cols, rows }}
 */
export function buildDefaultOffice() {
  const tileMap = createTileMap(COLS, ROWS);
  const furniture = [];
  const seats = [];
  const blockedTiles = new Set();

  // ─── Floor ─────────────────────────────────────────────
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      tileMap[r][c] = TileType.FLOOR;
    }
  }

  // ─── Walls (top row + left/right edges) ────────────────
  for (let c = 0; c < COLS; c++) {
    tileMap[0][c] = TileType.WALL;
  }
  for (let r = 0; r < ROWS; r++) {
    tileMap[r][0] = TileType.WALL;
    tileMap[r][COLS - 1] = TileType.WALL;
  }

  // ─── Desks & Seats (6 workstations) ────────────────────
  // Layout: 2 rows of 3 desks

  // Row 1: desks at row 3 (agent sits at row 4)
  _addWorkstation(furniture, seats, blockedTiles, 3,  3);  // Left
  _addWorkstation(furniture, seats, blockedTiles, 9,  3);  // Center
  _addWorkstation(furniture, seats, blockedTiles, 15, 3);  // Right

  // Row 2: desks at row 9 (agent sits at row 10)
  _addWorkstation(furniture, seats, blockedTiles, 3,  9);  // Left
  _addWorkstation(furniture, seats, blockedTiles, 9,  9);  // Center
  _addWorkstation(furniture, seats, blockedTiles, 15, 9);  // Right

  // ─── Plants ────────────────────────────────────────────
  _addFurniture(furniture, blockedTiles, 'plant', 1, 1);
  _addFurniture(furniture, blockedTiles, 'plant', COLS - 2, 1);
  _addFurniture(furniture, blockedTiles, 'plant', 1, ROWS - 3);
  _addFurniture(furniture, blockedTiles, 'plant', COLS - 2, ROWS - 3);

  // ─── Bookshelves (against top wall) ────────────────────
  _addFurniture(furniture, blockedTiles, 'bookshelf', 7, 1);
  _addFurniture(furniture, blockedTiles, 'bookshelf', 17, 1);

  // ─── Water Cooler ──────────────────────────────────────
  _addFurniture(furniture, blockedTiles, 'cooler', 12, ROWS - 3);

  // ─── Whiteboard ────────────────────────────────────────
  _addFurniture(furniture, blockedTiles, 'whiteboard', 21, 7);

  // ─── Desk Lamps (on desks) ─────────────────────────────
  _addFurniture(furniture, blockedTiles, 'lamp', 5, 2);
  _addFurniture(furniture, blockedTiles, 'lamp', 11, 2);
  _addFurniture(furniture, blockedTiles, 'lamp', 17, 2);
  _addFurniture(furniture, blockedTiles, 'lamp', 5, 8);
  _addFurniture(furniture, blockedTiles, 'lamp', 11, 8);
  _addFurniture(furniture, blockedTiles, 'lamp', 17, 8);

  return { tileMap, furniture, seats, blockedTiles, cols: COLS, rows: ROWS };
}

// ─── Private ───────────────────────────────────────────────────

function _addWorkstation(furniture, seats, blocked, col, row) {
  // Desk (2 tiles wide at row)
  furniture.push({
    type: 'desk',
    col,
    row,
    zY: row, // for z-sorting
  });
  blocked.add(`${col},${row}`);
  blocked.add(`${col + 1},${row}`);

  // Monitor on desk
  furniture.push({
    type: 'monitor',
    col,
    row,
    zY: row - 0.5, // slightly behind desk
  });

  // Chair in front of desk (row + 1)
  furniture.push({
    type: 'chair',
    col,
    row: row + 1,
    zY: row + 1,
  });

  // Seat position = where the character sits (on the chair tile)
  seats.push({
    col: col,
    row: row + 1,
    deskCol: col,
    deskRow: row,
  });
}

function _addFurniture(furniture, blocked, type, col, row) {
  furniture.push({
    type,
    col,
    row,
    zY: row,
  });

  // Block tiles based on furniture type
  const sizes = {
    plant: [[0, 0]],
    bookshelf: [[0, 0], [0, 1]],
    cooler: [[0, 0]],
    whiteboard: [[0, 0], [1, 0]],
    lamp: [], // lamps sit on desks, don't block
  };

  const blockTiles = sizes[type] || [[0, 0]];
  for (const [dc, dr] of blockTiles) {
    blocked.add(`${col + dc},${row + dr}`);
  }
}

export { COLS, ROWS };
