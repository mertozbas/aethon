/**
 * AETHON Pixel Office — Game Engine
 *
 * Main game loop with delta-time, Z-sorted rendering pipeline,
 * character management, and agent event routing.
 *
 * Rendering order: Floor → Walls → Furniture (z-sorted) → Characters (z-sorted) → Bubbles → Labels
 */

import { TILE_SIZE } from './spriteCache.js';
import { getCharSprite, getFurnitureSprite, getBubbleSprite, clearCache } from './spriteCache.js';
import { TILE_FLOOR, TILE_WALL, FURNITURE_DEFS, PALETTES, BUBBLE_THINKING, BUBBLE_PERMISSION } from './spriteData.js';
import { TileType } from './tileMap.js';
import { buildDefaultOffice } from './officeLayout.js';
import {
  createCharacter, updateCharacter, setActive, setInactive,
  getCharacterSprite, processPendingWalk, CharState,
} from './characters.js';

const MAX_DELTA = 0.1; // Cap delta time to prevent huge jumps
const IDLE_TIMEOUT_MS = 12000; // revert a character to idle after this much quiet

// Specialist role → palette index (matches the legend: Coder/Researcher/Analyst/Planner).
const ROLE_PALETTE = { coder: 0, researcher: 1, analyst: 2, planner: 3 };
const LABEL_FONT = '10px monospace';
const LABEL_COLOR = '#00d4ff';
const LABEL_BG = 'rgba(10, 10, 26, 0.8)';

export class PixelOfficeEngine {
  /**
   * @param {HTMLCanvasElement} canvas
   */
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.zoom = 2;

    // Build office
    const office = buildDefaultOffice();
    this.tileMap = office.tileMap;
    this.furniture = office.furniture;
    this.seats = office.seats;
    this.blockedTiles = office.blockedTiles;
    this.cols = office.cols;
    this.rows = office.rows;

    // Characters
    /** @type {Map<string, Object>} agentKey → character */
    this.characters = new Map();
    this._nextPaletteIdx = 0;
    this._assignedSeats = new Set(); // "col,row" of taken seats

    // Game loop
    this._running = false;
    this._lastTime = 0;
    this._rafId = null;

    // Size the canvas
    this._resize();
  }

  /** Start the game loop. */
  start() {
    if (this._running) return;
    this._running = true;
    this._lastTime = 0;
    this._rafId = requestAnimationFrame((t) => this._frame(t));
  }

  /** Stop the game loop. */
  stop() {
    this._running = false;
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
  }

  /** Resize canvas to fit container. */
  _resize() {
    const w = this.cols * TILE_SIZE * this.zoom;
    const h = this.rows * TILE_SIZE * this.zoom;
    this.canvas.width = w;
    this.canvas.height = h;
    this.canvas.style.width = w + 'px';
    this.canvas.style.height = h + 'px';
  }

  /** Set zoom level (1, 2, 3). */
  setZoom(z) {
    this.zoom = Math.max(1, Math.min(4, z));
    clearCache();
    this._resize();
  }

  // ─── Agent Integration ─────────────────────────────────

  /**
   * Add or update an agent in the office.
   * @param {string} agentKey — Unique agent identifier (e.g. session_id)
   * @param {string} agentName — Display name
   * @param {boolean} isActive — Currently working?
   * @param {string|null} toolName — Current tool
   */
  setAgent(agentKey, agentName, isActive = false, toolName = null) {
    let char = this.characters.get(agentKey);

    if (!char) {
      // New agent — create character
      char = this._spawnCharacter(agentKey, agentName);
      this.characters.set(agentKey, char);
    }

    // Update activity
    char.name = agentName;
    if (isActive) {
      char._lastActivity = performance.now();
      setActive(char, toolName);
    } else if (char.isActive) {
      setInactive(char);
    }
  }

  /**
   * Ensure a character exists for a roster agent WITHOUT forcing it active.
   * Roster sync should only confirm presence; real activity comes from events.
   * @param {string} agentKey
   * @param {string} agentName
   */
  ensureAgent(agentKey, agentName) {
    let char = this.characters.get(agentKey);
    if (!char) {
      char = this._spawnCharacter(agentKey, agentName);
      this.characters.set(agentKey, char);
    }
    char.name = agentName;
    return char;
  }

  /**
   * Remove an agent from the office.
   * @param {string} agentKey
   */
  removeAgent(agentKey) {
    const char = this.characters.get(agentKey);
    if (!char) return;

    // Free seat
    if (char.seat) {
      this._assignedSeats.delete(`${char.seat.col},${char.seat.row}`);
    }

    // Start despawn animation
    char.despawning = true;
    char.despawnTimer = 0;

    // Remove after animation
    setTimeout(() => {
      this.characters.delete(agentKey);
    }, 500);
  }

  /**
   * Handle a WebSocket agent event.
   * @param {Object} data — Event data from 'agents' or 'telemetry' channel
   */
  onAgentEvent(data) {
    // Determine agent key + name
    const sessionId = data.session_id || data.agent_id || 'unknown';
    const agentName = data.agent_name || data.name || sessionId.split(':').pop() || 'Agent';

    if (data.event === 'tool_start') {
      this.setAgent(sessionId, agentName, true, data.tool_name);
    } else if (data.event === 'tool_end') {
      // Keep active, clear tool
      this.setAgent(sessionId, agentName, true, null);
    } else if (data.type === 'tool' && data.status) {
      this.setAgent(sessionId, agentName, true, data.name);
    } else if (data.type === 'model') {
      this.setAgent(sessionId, agentName, true, null);
    }
  }

  /**
   * Sync agent list from /api/agents/active data.
   * @param {Object[]} agents — Array of { session_id, agent_name, agent_id }
   */
  syncAgents(agents) {
    const rosterKeys = new Set();

    for (const a of agents) {
      const key = a.session_id || a.agent_id || 'unknown';
      const name = a.agent_name || 'Agent';
      rosterKeys.add(key);
      this.ensureAgent(key, name);  // present, but idle until real activity arrives
    }

    // Despawn characters whose agent has left the roster.
    for (const [key, char] of this.characters) {
      if (!rosterKeys.has(key) && !char.despawning) {
        this.removeAgent(key);
      }
    }
  }

  // ─── Private: Character Management ─────────────────────

  _spawnCharacter(agentKey, agentName) {
    // Find an available seat
    let seat = null;
    for (const s of this.seats) {
      const sKey = `${s.col},${s.row}`;
      if (!this._assignedSeats.has(sKey)) {
        seat = { col: s.col, row: s.row };
        this._assignedSeats.add(sKey);
        break;
      }
    }

    // Palette: specialists get a fixed color matching the legend; main/session
    // agents take the remaining palettes round-robin.
    const pi = this._paletteForAgent(agentKey, agentName);

    // Spawn position: at a walkable tile near entrance (bottom-center)
    const spawnCol = Math.floor(this.cols / 2);
    const spawnRow = this.rows - 2;

    return createCharacter({
      id: agentKey,
      name: agentName,
      paletteIndex: pi,
      col: spawnCol,
      row: spawnRow,
      seat,
    });
  }

  /** Pick a palette index: specialists fixed by role, others round-robin (Builder/Creative). */
  _paletteForAgent(agentKey, agentName) {
    let role = '';
    if (agentKey && agentKey.startsWith('specialist:')) {
      role = (agentKey.split(':')[1] || '').toLowerCase();
    } else {
      role = (agentName || '').toLowerCase();
    }
    if (role in ROLE_PALETTE) return ROLE_PALETTE[role];
    const pi = 4 + (this._nextPaletteIdx % 2); // Builder / Creative
    this._nextPaletteIdx++;
    return pi;
  }

  // ─── Game Loop ─────────────────────────────────────────

  _frame(time) {
    if (!this._running) return;

    const dt = this._lastTime === 0 ? 0 : Math.min((time - this._lastTime) / 1000, MAX_DELTA);
    this._lastTime = time;

    this._update(dt);
    this._render();

    this._rafId = requestAnimationFrame((t) => this._frame(t));
  }

  _update(dt) {
    const now = performance.now();
    for (const [key, char] of this.characters) {
      // Revert to idle after a quiet period so the working/idle states reflect
      // real activity instead of staying "busy" forever.
      if (char.isActive && char._lastActivity && now - char._lastActivity > IDLE_TIMEOUT_MS) {
        setInactive(char);
      }
      // Process pending seat walks
      processPendingWalk(char, this.tileMap, this.blockedTiles);
      // Update character
      updateCharacter(char, dt, this.tileMap, this.blockedTiles);
    }
  }

  // ─── Rendering Pipeline ────────────────────────────────

  _render() {
    const ctx = this.ctx;
    const z = this.zoom;
    const ts = TILE_SIZE * z;

    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // 1. Render floor tiles
    this._renderTiles(ctx, z, ts);

    // 2. Collect all drawables for z-sorting
    const drawables = [];

    // Furniture
    for (const f of this.furniture) {
      drawables.push({
        zY: f.zY || f.row,
        draw: () => this._drawFurniture(ctx, f, z, ts),
      });
    }

    // Characters
    for (const [key, char] of this.characters) {
      if (char.spawnTimer > 0) continue; // Still spawning
      drawables.push({
        zY: char.row + 0.5, // Characters sort slightly behind their row
        draw: () => this._drawCharacter(ctx, char, z, ts),
      });
    }

    // 3. Sort by Y (bottom objects draw last / in front)
    drawables.sort((a, b) => a.zY - b.zY);

    // 4. Draw all
    for (const d of drawables) {
      d.draw();
    }

    // 5. Labels (always on top)
    for (const [key, char] of this.characters) {
      if (char.spawnTimer > 0 || char.despawning) continue;
      this._drawLabel(ctx, char, z, ts);
    }

    // 6. Bubbles (always on top)
    for (const [key, char] of this.characters) {
      if (char.bubble && !char.despawning) {
        this._drawBubble(ctx, char, z, ts);
      }
    }
  }

  _renderTiles(ctx, z, ts) {
    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        const type = this.tileMap[r][c];
        if (type === TileType.VOID) continue;

        const sprite = type === TileType.WALL ? TILE_WALL : TILE_FLOOR;
        if (!sprite) continue;

        const cached = getFurnitureSprite(sprite, z);
        ctx.drawImage(cached, c * ts, r * ts);
      }
    }
  }

  _drawFurniture(ctx, f, z, ts) {
    const def = FURNITURE_DEFS[f.type];
    if (!def) return;

    const cached = getFurnitureSprite(def.sprite, z);
    ctx.drawImage(cached, f.col * ts, f.row * ts);
  }

  _drawCharacter(ctx, char, z, ts) {
    const { template, mirror } = getCharacterSprite(char);
    if (!template) return;

    const cached = getCharSprite(template, char.palette, z, mirror);

    // Character pixel position
    const px = char.x * z;
    const py = char.y * z;

    // Characters are 16×24, offset to center on tile
    const charW = cached.width;
    const charH = cached.height;
    const offsetX = (ts - charW) / 2;
    const offsetY = ts - charH; // Feet align to bottom of tile

    // Spawn/despawn opacity
    let alpha = 1;
    if (char.spawnTimer > 0) {
      alpha = 1 - (char.spawnTimer / 0.5);
    }
    if (char.despawning) {
      alpha = Math.max(0, 1 - char.despawnTimer * 2);
    }

    if (alpha < 1) ctx.globalAlpha = alpha;
    ctx.drawImage(cached, px + offsetX, py + offsetY);
    if (alpha < 1) ctx.globalAlpha = 1;
  }

  _drawLabel(ctx, char, z, ts) {
    const px = char.x * z + ts / 2;
    const py = char.y * z - 6 * z;

    const name = char.name || 'Agent';
    const displayName = name.length > 12 ? name.slice(0, 11) + '\u2026' : name;

    ctx.font = `bold ${Math.max(9, 5 * z)}px monospace`;
    const metrics = ctx.measureText(displayName);
    const tw = metrics.width;
    const th = 5 * z + 4;

    // Background pill
    ctx.fillStyle = LABEL_BG;
    const rx = px - tw / 2 - 4;
    const ry = py - th / 2;
    const rw = tw + 8;
    const rh = th;
    _roundRect(ctx, rx, ry, rw, rh, 3);
    ctx.fill();

    // Border
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.3)';
    ctx.lineWidth = 1;
    _roundRect(ctx, rx, ry, rw, rh, 3);
    ctx.stroke();

    // Text
    ctx.fillStyle = LABEL_COLOR;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(displayName, px, py);
  }

  _drawBubble(ctx, char, z, ts) {
    const spriteObj = char.bubble === 'thinking' ? BUBBLE_THINKING : BUBBLE_PERMISSION;
    const cached = getBubbleSprite(spriteObj, z);

    const px = char.x * z + ts / 2 - cached.width / 2;
    const py = char.y * z - cached.height - 4 * z;

    // Fade out
    let alpha = 1;
    if (char.bubbleTimer < 0.5) {
      alpha = char.bubbleTimer / 0.5;
    }

    if (alpha < 1) ctx.globalAlpha = alpha;
    ctx.drawImage(cached, px, py);
    if (alpha < 1) ctx.globalAlpha = 1;
  }
}

// ─── Helpers ───────────────────────────────────────────────────

function _roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}
