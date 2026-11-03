import { esc, formatSize } from '../core/format.js';
import { empty } from './primitives.js';

const WIDTH = 600;
const HEIGHT = 190;
const PADDING = 32;

const dateLabel = (iso) => esc(new Date(iso).toLocaleString());

/** A line chart of allocated space across scans. ``points`` are ``{finished, used, total}``. */
export function trendChart(points) {
  if (points.length < 2) {
    return empty('A second completed scan will start the chart. No historical data is fabricated.');
  }
  const max = Math.max(...points.map((p) => p.total));
  const x = (i) => PADDING + (i * (WIDTH - 2 * PADDING)) / (points.length - 1);
  const y = (bytes) => HEIGHT - PADDING - (bytes / max) * (HEIGHT - 2 * PADDING);
  const line = points.map((p, i) => `${x(i)},${y(p.used)}`).join(' ');
  const dots = points.map((p, i) => `
    <circle cx="${x(i)}" cy="${y(p.used)}" r="3" class="chart-dot">
      <title>${esc(p.finished)}: ${formatSize(p.used)} allocated</title>
    </circle>`).join('');

  return `
    <svg class="trend-chart" viewBox="0 0 ${WIDTH} ${HEIGHT}" role="img"
         aria-label="Allocated storage over ${points.length} completed scans">
      <line x1="${PADDING}" y1="${HEIGHT - PADDING}" x2="${WIDTH - PADDING}" y2="${HEIGHT - PADDING}" class="chart-axis"/>
      <text x="0" y="${PADDING}">${formatSize(max)}</text>
      <text x="3" y="${HEIGHT - PADDING}">0</text>
      <polyline points="${line}" fill="none" class="chart-line"/>
      ${dots}
    </svg>
    <div class="chart-dates"><span>${dateLabel(points[0].finished)}</span><span>${dateLabel(points.at(-1).finished)}</span></div>`;
}
