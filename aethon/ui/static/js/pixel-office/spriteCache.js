/**
 * AETHON Pixel Office — Sprite Cache
 *
 * Converts pixel-art string templates to cached HTMLCanvasElement.
 * Supports palette mapping, zoom levels, and horizontal mirroring.
 * Uses WeakMap for garbage-friendly caching.
 */

const TILE_SIZE = 16;

/** @type {Map<number, Map<string, HTMLCanvasElement>>} zoom → cacheKey → canvas */
const _cache = new Map();

/**
 * Render a character sprite template with a palette and return cached canvas.
 * @param {string[]} template — Array of 16-char strings (palette keys)
 * @param {Object} palette — Map of char → hex color
 * @param {number} [zoom=2] — Pixel scale
 * @param {boolean} [mirror=false] — Flip horizontally (for left-facing)
 * @returns {HTMLCanvasElement}
 */
export function getCharSprite(template, palette, zoom = 2, mirror = false) {
  const key = _charKey(template, palette, mirror);
  return _getOrCreate(key, zoom, () => _renderCharTemplate(template, palette, zoom, mirror));
}

/**
 * Render a furniture/tile sprite (direct color maps) and return cached canvas.
 * @param {Object} spriteObj — { width, height, colors, data }
 * @param {number} [zoom=2]
 * @returns {HTMLCanvasElement}
 */
export function getFurnitureSprite(spriteObj, zoom = 2) {
  const key = `furn_${spriteObj.width}x${spriteObj.height}_${_hashData(spriteObj.data)}`;
  return _getOrCreate(key, zoom, () => _renderFurnitureSprite(spriteObj, zoom));
}

/**
 * Render a speech bubble sprite.
 * @param {Object} spriteObj — { width, height, colors, data }
 * @param {number} [zoom=2]
 * @returns {HTMLCanvasElement}
 */
export function getBubbleSprite(spriteObj, zoom = 2) {
  return getFurnitureSprite(spriteObj, zoom);
}

// ─── Private ───────────────────────────────────────────────────

function _getOrCreate(key, zoom, createFn) {
  if (!_cache.has(zoom)) _cache.set(zoom, new Map());
  const zoomCache = _cache.get(zoom);
  if (zoomCache.has(key)) return zoomCache.get(key);
  const canvas = createFn();
  zoomCache.set(key, canvas);
  return canvas;
}

function _charKey(template, palette, mirror) {
  // Use palette name + template first row hash + mirror flag
  const name = palette.name || 'x';
  const tHash = template[0] + template[3] + template[8] + template[14];
  return `c_${name}_${tHash}_${mirror ? 'L' : 'R'}`;
}

function _hashData(data) {
  // Simple hash from first + last rows
  return (data[0] || '').slice(0, 8) + (data[data.length - 1] || '').slice(0, 8);
}

function _renderCharTemplate(template, palette, zoom, mirror) {
  const rows = template.length;
  const cols = template[0].length;
  const canvas = document.createElement('canvas');
  canvas.width = cols * zoom;
  canvas.height = rows * zoom;
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;

  for (let r = 0; r < rows; r++) {
    const row = template[r];
    for (let c = 0; c < cols; c++) {
      const ch = row[c];
      if (ch === '_' || ch === ' ') continue;

      const color = palette[ch];
      if (!color) continue;

      ctx.fillStyle = color;
      const x = mirror ? (cols - 1 - c) * zoom : c * zoom;
      ctx.fillRect(x, r * zoom, zoom, zoom);
    }
  }
  return canvas;
}

function _renderFurnitureSprite(spriteObj, zoom) {
  const { width, height, colors, data } = spriteObj;
  const canvas = document.createElement('canvas');

  // Auto-detect dimensions from data
  const rows = data.length;
  const cols = Math.max(...data.map(r => r.length));
  canvas.width = cols * zoom;
  canvas.height = rows * zoom;
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;

  for (let r = 0; r < rows; r++) {
    const row = data[r];
    for (let c = 0; c < row.length; c++) {
      const ch = row[c];
      if (ch === '_' || ch === ' ') continue;

      const color = colors[ch];
      if (!color) continue;

      ctx.fillStyle = color;
      ctx.fillRect(c * zoom, r * zoom, zoom, zoom);
    }
  }
  return canvas;
}

/**
 * Clear all cached sprites (call on zoom change).
 */
export function clearCache() {
  _cache.clear();
}

export { TILE_SIZE };
