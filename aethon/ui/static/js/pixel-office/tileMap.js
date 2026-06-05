/**
 * AETHON Pixel Office — Tile Map & BFS Pathfinding
 *
 * 2D grid-based tile system with walkability and BFS shortest-path.
 * Tile types: FLOOR, WALL, VOID.
 * Blocked tiles tracked separately (furniture, other characters).
 */

export const TileType = {
  VOID:  0,
  FLOOR: 1,
  WALL:  2,
};

/**
 * Create a tile map with the given dimensions.
 * @param {number} cols
 * @param {number} rows
 * @returns {number[][]} — 2D array of TileType
 */
export function createTileMap(cols, rows) {
  const map = [];
  for (let r = 0; r < rows; r++) {
    map.push(new Array(cols).fill(TileType.VOID));
  }
  return map;
}

/**
 * Check if a tile is walkable.
 * @param {number[][]} map
 * @param {number} col
 * @param {number} row
 * @param {Set<string>} blockedTiles — Set of "col,row" strings
 * @returns {boolean}
 */
export function isWalkable(map, col, row, blockedTiles) {
  if (row < 0 || row >= map.length) return false;
  if (col < 0 || col >= map[0].length) return false;
  const tile = map[row][col];
  if (tile !== TileType.FLOOR) return false;
  if (blockedTiles.has(`${col},${row}`)) return false;
  return true;
}

/**
 * BFS pathfinding from start to end.
 * Returns path EXCLUDING start, INCLUDING end.
 * Returns null if no path found.
 *
 * @param {number[][]} map
 * @param {{col: number, row: number}} start
 * @param {{col: number, row: number}} end
 * @param {Set<string>} blockedTiles
 * @param {Set<string>} [unblockTiles] — Tiles to temporarily unblock (e.g. own seat)
 * @returns {{col: number, row: number}[]|null}
 */
export function findPath(map, start, end, blockedTiles, unblockTiles = null) {
  const endKey = `${end.col},${end.row}`;

  // Temporarily unblock target tile for pathfinding
  const tempBlocked = new Set(blockedTiles);
  if (unblockTiles) {
    for (const t of unblockTiles) tempBlocked.delete(t);
  }
  // Always unblock the destination
  tempBlocked.delete(endKey);

  // Check if destination is walkable (ignoring blocks)
  if (end.row < 0 || end.row >= map.length) return null;
  if (end.col < 0 || end.col >= map[0].length) return null;
  if (map[end.row][end.col] !== TileType.FLOOR) return null;

  const startKey = `${start.col},${start.row}`;
  if (startKey === endKey) return [];

  // BFS
  const visited = new Set([startKey]);
  const parent = new Map();
  const queue = [{ col: start.col, row: start.row }];

  // 4-directional movement
  const dirs = [
    { dc: 0, dr: -1 }, // up
    { dc: 0, dr:  1 }, // down
    { dc: -1, dr: 0 }, // left
    { dc:  1, dr: 0 }, // right
  ];

  while (queue.length > 0) {
    const curr = queue.shift();
    const currKey = `${curr.col},${curr.row}`;

    for (const d of dirs) {
      const nc = curr.col + d.dc;
      const nr = curr.row + d.dr;
      const nKey = `${nc},${nr}`;

      if (visited.has(nKey)) continue;
      if (!isWalkable(map, nc, nr, tempBlocked)) continue;

      visited.add(nKey);
      parent.set(nKey, currKey);

      if (nKey === endKey) {
        // Reconstruct path
        return _reconstructPath(parent, startKey, endKey);
      }

      queue.push({ col: nc, row: nr });
    }
  }

  return null; // No path found
}

/**
 * Get all walkable tiles.
 * @param {number[][]} map
 * @param {Set<string>} blockedTiles
 * @returns {{col: number, row: number}[]}
 */
export function getWalkableTiles(map, blockedTiles) {
  const tiles = [];
  for (let r = 0; r < map.length; r++) {
    for (let c = 0; c < map[0].length; c++) {
      if (isWalkable(map, c, r, blockedTiles)) {
        tiles.push({ col: c, row: r });
      }
    }
  }
  return tiles;
}

/**
 * Get a random walkable tile.
 * @param {number[][]} map
 * @param {Set<string>} blockedTiles
 * @returns {{col: number, row: number}|null}
 */
export function getRandomWalkable(map, blockedTiles) {
  const tiles = getWalkableTiles(map, blockedTiles);
  if (tiles.length === 0) return null;
  return tiles[Math.floor(Math.random() * tiles.length)];
}

// ─── Private ───────────────────────────────────────────────────

function _reconstructPath(parent, startKey, endKey) {
  const path = [];
  let key = endKey;
  while (key !== startKey) {
    const [c, r] = key.split(',').map(Number);
    path.unshift({ col: c, row: r });
    key = parent.get(key);
    if (!key) return null; // Should not happen
  }
  return path;
}
