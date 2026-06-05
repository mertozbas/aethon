/**
 * AETHON Pixel Office — Character System
 *
 * State machine: IDLE → WALK → TYPE/READ
 * Smooth interpolated movement, wander behavior, seat assignment.
 * Mirrors the pixel-agents project architecture.
 */

import { CHAR_SPRITES, PALETTES, READING_TOOLS } from './spriteData.js';
import { findPath, getRandomWalkable } from './tileMap.js';

// ─── Constants ─────────────────────────────────────────────────
const TILE_SIZE = 16;
const WALK_SPEED_PX_PER_SEC = 48;
const WALK_FRAME_DURATION = 0.15;  // seconds per walk frame
const TYPE_FRAME_DURATION = 0.3;   // seconds per type frame
const WANDER_PAUSE_MIN = 2.0;
const WANDER_PAUSE_MAX = 12.0;
const WANDER_MOVES_BEFORE_REST_MIN = 3;
const WANDER_MOVES_BEFORE_REST_MAX = 6;
const SEAT_REST_MIN = 60.0;
const SEAT_REST_MAX = 120.0;

export const CharState = {
  IDLE: 'idle',
  WALK: 'walk',
  TYPE: 'type',
  READ: 'read',
};

/**
 * Create a new character.
 * @param {Object} opts
 * @param {number} opts.id
 * @param {string} opts.name — Agent name
 * @param {number} opts.paletteIndex — Index into PALETTES
 * @param {number} opts.col — Tile column
 * @param {number} opts.row — Tile row
 * @param {Object} [opts.seat] — { col, row } of assigned desk seat
 * @returns {Object} character
 */
export function createCharacter({ id, name, paletteIndex, col, row, seat = null }) {
  return {
    id,
    name,
    palette: PALETTES[paletteIndex % PALETTES.length],
    paletteIndex: paletteIndex % PALETTES.length,

    // Position (pixel-level for smooth interpolation)
    x: col * TILE_SIZE,
    y: row * TILE_SIZE,
    col,
    row,

    // State machine
    state: CharState.IDLE,
    direction: 'down',
    isActive: false,
    currentTool: null,

    // Seat assignment
    seat, // { col, row } or null

    // Walk state
    path: [],
    pathIndex: 0,
    moveProgress: 0,  // 0→1 progress between tiles
    fromCol: col,
    fromRow: row,

    // Animation
    animFrame: 0,
    animTimer: 0,

    // Wander behavior (when inactive)
    wanderPauseTimer: _randRange(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX),
    wanderMoves: 0,
    wanderLimit: _randInt(WANDER_MOVES_BEFORE_REST_MIN, WANDER_MOVES_BEFORE_REST_MAX),
    isResting: false,
    restTimer: 0,

    // Speech bubble
    bubble: null, // null | 'thinking' | 'permission'
    bubbleTimer: 0,

    // Spawn animation
    spawnTimer: 0.5,
    despawning: false,
    despawnTimer: 0,
  };
}

/**
 * Update character state for one frame.
 * @param {Object} char — Character object
 * @param {number} dt — Delta time in seconds
 * @param {number[][]} tileMap
 * @param {Set<string>} blockedTiles
 */
export function updateCharacter(char, dt, tileMap, blockedTiles) {
  // Spawn animation
  if (char.spawnTimer > 0) {
    char.spawnTimer -= dt;
    return;
  }

  // Despawn animation
  if (char.despawning) {
    char.despawnTimer += dt;
    return;
  }

  // Update animation timer
  char.animTimer += dt;

  // Bubble timer
  if (char.bubble && char.bubbleTimer > 0) {
    char.bubbleTimer -= dt;
    if (char.bubbleTimer <= 0) char.bubble = null;
  }

  switch (char.state) {
    case CharState.WALK:
      _updateWalk(char, dt, tileMap, blockedTiles);
      break;
    case CharState.TYPE:
    case CharState.READ:
      _updateSeated(char, dt);
      break;
    case CharState.IDLE:
      _updateIdle(char, dt, tileMap, blockedTiles);
      break;
  }
}

/**
 * Set character as active (agent is working).
 * @param {Object} char
 * @param {string|null} toolName — Current tool being used
 */
export function setActive(char, toolName = null) {
  char.isActive = true;
  char.currentTool = toolName;

  if (char.seat) {
    if (char.state !== CharState.TYPE && char.state !== CharState.READ) {
      // Walk to seat if not already there
      if (char.col !== char.seat.col || char.row !== char.seat.row) {
        _walkToSeat(char);
      } else {
        _sitDown(char);
      }
    } else {
      // Update seated state based on tool
      char.state = _isReadingTool(toolName) ? CharState.READ : CharState.TYPE;
    }
  } else {
    // No seat — just type in place
    char.state = _isReadingTool(toolName) ? CharState.READ : CharState.TYPE;
  }
}

/**
 * Set character as inactive (agent idle).
 * @param {Object} char
 */
export function setInactive(char) {
  char.isActive = false;
  char.currentTool = null;

  if (char.state === CharState.TYPE || char.state === CharState.READ) {
    // Stand up and start wandering
    char.state = CharState.IDLE;
    char.wanderPauseTimer = _randRange(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX);
    char.wanderMoves = 0;
    char.wanderLimit = _randInt(WANDER_MOVES_BEFORE_REST_MIN, WANDER_MOVES_BEFORE_REST_MAX);
  }
}

/**
 * Get the current sprite data for a character.
 * @param {Object} char
 * @returns {{ template: string[], mirror: boolean }}
 */
export function getCharacterSprite(char) {
  const sprites = CHAR_SPRITES;
  let template;
  let mirror = false;

  switch (char.state) {
    case CharState.TYPE: {
      const idx = Math.floor(char.animTimer / TYPE_FRAME_DURATION) % 2;
      template = sprites.type[idx];
      break;
    }
    case CharState.READ: {
      const idx = Math.floor(char.animTimer / TYPE_FRAME_DURATION) % 2;
      template = sprites.read[idx];
      break;
    }
    case CharState.WALK: {
      const dir = char.direction;
      if (dir === 'left') {
        const idx = Math.floor(char.animTimer / WALK_FRAME_DURATION) % 3;
        template = sprites.right.walk[idx];
        mirror = true;
      } else {
        const dirSprites = sprites[dir] || sprites.down;
        const idx = Math.floor(char.animTimer / WALK_FRAME_DURATION) % 3;
        template = dirSprites.walk[idx];
      }
      break;
    }
    default: { // IDLE
      const dir = char.direction;
      if (dir === 'left') {
        template = sprites.right.idle;
        mirror = true;
      } else {
        template = (sprites[dir] || sprites.down).idle;
      }
      break;
    }
  }

  return { template, mirror };
}

// ─── Private Update Handlers ───────────────────────────────────

function _updateWalk(char, dt, tileMap, blockedTiles) {
  if (!char.path || char.pathIndex >= char.path.length) {
    // Path complete — arrive at destination
    _arriveAtDestination(char);
    return;
  }

  const target = char.path[char.pathIndex];
  const speed = WALK_SPEED_PX_PER_SEC / TILE_SIZE; // tiles per second
  char.moveProgress += speed * dt;

  if (char.moveProgress >= 1) {
    // Arrived at next tile
    char.col = target.col;
    char.row = target.row;
    char.x = target.col * TILE_SIZE;
    char.y = target.row * TILE_SIZE;
    char.moveProgress = 0;
    char.fromCol = target.col;
    char.fromRow = target.row;
    char.pathIndex++;

    // Update direction for next segment
    if (char.pathIndex < char.path.length) {
      const next = char.path[char.pathIndex];
      char.direction = _getDirection(char.col, char.row, next.col, next.row);
    }
  } else {
    // Interpolate position
    char.x = (char.fromCol + (target.col - char.fromCol) * char.moveProgress) * TILE_SIZE;
    char.y = (char.fromRow + (target.row - char.fromRow) * char.moveProgress) * TILE_SIZE;
  }
}

function _updateSeated(char, dt) {
  // Just animate — stay seated
  // If somehow deactivated while seated, transition to idle
  if (!char.isActive) {
    char.state = CharState.IDLE;
    char.wanderPauseTimer = _randRange(1, 3);
  }
}

function _updateIdle(char, dt, tileMap, blockedTiles) {
  // If active and has seat, walk to it
  if (char.isActive && char.seat) {
    _walkToSeat(char);
    return;
  }

  // If active without seat, start typing in place
  if (char.isActive) {
    char.state = CharState.TYPE;
    return;
  }

  // Resting at seat?
  if (char.isResting) {
    char.restTimer -= dt;
    if (char.restTimer <= 0) {
      char.isResting = false;
      char.wanderMoves = 0;
      char.wanderLimit = _randInt(WANDER_MOVES_BEFORE_REST_MIN, WANDER_MOVES_BEFORE_REST_MAX);
    }
    return;
  }

  // Wander pause
  char.wanderPauseTimer -= dt;
  if (char.wanderPauseTimer > 0) return;

  // Time to wander
  if (char.wanderMoves >= char.wanderLimit && char.seat) {
    // Go back to seat for rest
    _walkToSeat(char);
    char.isResting = true;
    char.restTimer = _randRange(SEAT_REST_MIN, SEAT_REST_MAX);
    return;
  }

  // Pick random walkable tile and walk there
  const target = getRandomWalkable(tileMap, blockedTiles);
  if (!target) return;

  const path = findPath(tileMap, { col: char.col, row: char.row }, target, blockedTiles);
  if (path && path.length > 0) {
    // Limit wander path length
    const maxLen = 8;
    const trimmedPath = path.slice(0, maxLen);
    _startWalk(char, trimmedPath);
    char.wanderMoves++;
  } else {
    char.wanderPauseTimer = _randRange(1, 3);
  }
}

function _arriveAtDestination(char) {
  char.path = [];
  char.pathIndex = 0;
  char.moveProgress = 0;

  if (char.isActive && char.seat && char.col === char.seat.col && char.row === char.seat.row) {
    _sitDown(char);
  } else if (char.isResting && char.seat && char.col === char.seat.col && char.row === char.seat.row) {
    // Resting at seat — stay idle
    char.state = CharState.IDLE;
    char.direction = 'down';
  } else {
    char.state = CharState.IDLE;
    char.wanderPauseTimer = _randRange(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX);
  }
}

function _walkToSeat(char) {
  if (!char.seat) return;
  if (char.col === char.seat.col && char.row === char.seat.row) {
    if (char.isActive) _sitDown(char);
    return;
  }
  // Path will be calculated by the engine (needs tileMap + blockedTiles)
  char._pendingSeatWalk = true;
}

function _sitDown(char) {
  char.state = _isReadingTool(char.currentTool) ? CharState.READ : CharState.TYPE;
  char.direction = 'down';
  char.animTimer = 0;
}

function _startWalk(char, path) {
  char.state = CharState.WALK;
  char.path = path;
  char.pathIndex = 0;
  char.moveProgress = 0;
  char.fromCol = char.col;
  char.fromRow = char.row;
  char.animTimer = 0;

  // Set initial direction
  if (path.length > 0) {
    char.direction = _getDirection(char.col, char.row, path[0].col, path[0].row);
  }
}

/**
 * Process pending seat walks (called from engine with tileMap access).
 * @param {Object} char
 * @param {number[][]} tileMap
 * @param {Set<string>} blockedTiles
 */
export function processPendingWalk(char, tileMap, blockedTiles) {
  if (!char._pendingSeatWalk || !char.seat) return;
  char._pendingSeatWalk = false;

  const unblock = new Set([`${char.seat.col},${char.seat.row}`]);
  const path = findPath(
    tileMap,
    { col: char.col, row: char.row },
    char.seat,
    blockedTiles,
    unblock
  );

  if (path && path.length > 0) {
    _startWalk(char, path);
  } else {
    // Can't reach seat — type in place
    if (char.isActive) {
      char.state = CharState.TYPE;
    }
  }
}

// ─── Helpers ───────────────────────────────────────────────────

function _getDirection(fromCol, fromRow, toCol, toRow) {
  const dc = toCol - fromCol;
  const dr = toRow - fromRow;
  if (Math.abs(dc) > Math.abs(dr)) {
    return dc > 0 ? 'right' : 'left';
  }
  return dr > 0 ? 'down' : 'up';
}

function _isReadingTool(toolName) {
  if (!toolName) return false;
  return READING_TOOLS.has(toolName.toLowerCase());
}

function _randRange(min, max) {
  return min + Math.random() * (max - min);
}

function _randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export { _startWalk as startWalk, TILE_SIZE };
