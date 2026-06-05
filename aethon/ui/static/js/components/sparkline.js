/**
 * AETHON Dashboard — Sparkline Mini-Chart
 *
 * Pure Canvas sparkline renderer. Zero dependencies.
 * Draws a smooth area chart with neon glow effect.
 *
 * Usage:
 *   import { drawSparkline } from './components/sparkline.js';
 *   const canvas = document.getElementById('my-canvas');
 *   drawSparkline(canvas, [3, 7, 2, 9, 5, 8], { color: '#00d4ff' });
 */

/**
 * Draw a sparkline chart on a canvas.
 * @param {HTMLCanvasElement} canvas
 * @param {number[]} data — Array of numeric values
 * @param {Object} [opts]
 * @param {string} [opts.color='#00d4ff'] — Line/fill color
 * @param {number} [opts.lineWidth=1.5] — Stroke width
 * @param {number} [opts.fillOpacity=0.15] — Area fill opacity (0-1)
 * @param {boolean} [opts.showDot=true] — Show dot on last value
 */
export function drawSparkline(canvas, data, opts = {}) {
  if (!canvas || !data || data.length < 2) return;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const color = opts.color || '#00d4ff';
  const lineWidth = opts.lineWidth || 1.5;
  const fillOpacity = opts.fillOpacity || 0.15;
  const showDot = opts.showDot !== false;

  // Use device pixel ratio for crisp rendering
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const w = rect.width || canvas.clientWidth || 120;
  const h = rect.height || canvas.clientHeight || 32;

  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.scale(dpr, dpr);

  // Clear
  ctx.clearRect(0, 0, w, h);

  // Compute min/max for normalization
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  // Padding so lines don't clip edges
  const padY = 3;
  const padX = 2;
  const chartW = w - padX * 2;
  const chartH = h - padY * 2;

  // Map data → canvas coordinates
  const step = chartW / (data.length - 1);
  const points = data.map((val, i) => ({
    x: padX + i * step,
    y: padY + chartH - ((val - min) / range) * chartH,
  }));

  // --- Area fill (gradient) ---
  const gradient = ctx.createLinearGradient(0, padY, 0, h);
  gradient.addColorStop(0, _rgba(color, fillOpacity));
  gradient.addColorStop(1, _rgba(color, 0));

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);

  // Smooth curve using quadratic bezier through midpoints
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx = (prev.x + curr.x) / 2;
    ctx.quadraticCurveTo(prev.x, prev.y, cpx, (prev.y + curr.y) / 2);
  }
  // Final segment to last point
  const last = points[points.length - 1];
  ctx.lineTo(last.x, last.y);

  // Close area path
  ctx.lineTo(last.x, h);
  ctx.lineTo(points[0].x, h);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // --- Line stroke ---
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);

  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx = (prev.x + curr.x) / 2;
    ctx.quadraticCurveTo(prev.x, prev.y, cpx, (prev.y + curr.y) / 2);
  }
  ctx.lineTo(last.x, last.y);

  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.stroke();

  // --- Glow effect (subtle) ---
  ctx.globalAlpha = 0.3;
  ctx.shadowColor = color;
  ctx.shadowBlur = 6;
  ctx.stroke();
  ctx.globalAlpha = 1;
  ctx.shadowBlur = 0;

  // --- Last-value dot ---
  if (showDot) {
    ctx.beginPath();
    ctx.arc(last.x, last.y, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    // Glow ring
    ctx.beginPath();
    ctx.arc(last.x, last.y, 4, 0, Math.PI * 2);
    ctx.strokeStyle = _rgba(color, 0.4);
    ctx.lineWidth = 1;
    ctx.stroke();
  }
}

/**
 * Parse hex color and apply alpha.
 * @param {string} hex
 * @param {number} alpha
 * @returns {string}
 */
function _rgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
