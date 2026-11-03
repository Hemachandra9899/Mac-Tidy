import { loading } from '../components/insight-rows.js';
import { measuredMetric, metric, metricRow } from '../components/metrics.js';
import { card, empty, notice } from '../components/primitives.js';
import { trendChart } from '../components/trend-chart.js';
import { esc, formatSize } from '../core/format.js';
import { shortPath } from '../core/selectors.js';
import { state } from '../core/state.js';

const MAX_POINTS_NOTE = 60;
const FOOTNOTE = 'The history stores 60 capacity points and only the latest two folder baselines to keep its own footprint small. Free-space changes include background app activity and APFS behavior.';
const NO_CHANGES = 'No comparable folder changed by at least 200 MB. Missing or partially read folders are not treated as reclaimed space.';

const changeRow = (change) => `
  <div class="insight-location">
    <div class="rowname">
      <b title="${esc(change.path)}">${esc(shortPath(change.path))}</b>
      <small>${formatSize(change.before)} → ${formatSize(change.after)}</small>
    </div>
    <strong class="${change.delta < 0 ? 'reduced' : 'increased'}">${change.delta > 0 ? '+' : '−'}${formatSize(Math.abs(change.delta))}</strong>
  </div>`;

/** Free-space metrics for the latest scan, and its change since the one before. */
function freeSpaceMetrics(points) {
  const last = points.at(-1);
  if (!last) return '';
  const previous = points.at(-2);
  const delta = previous ? last.free - previous.free : null;
  const label = delta === null ? 'Previous scan needed' : delta >= 0 ? 'Available-space increase' : 'Available-space decrease';
  return metricRow(
    metric('Available at latest scan', last.free, new Date(last.finished).toLocaleString()),
    measuredMetric(label, delta === null ? null : Math.abs(delta), 'Filesystem change; not proof that cleanup caused it'),
  );
}

export function trendsView() {
  const data = state.trends;
  if (!data) return loading();
  const { points } = data;
  const emptyChanges = empty(points.length < 2 ? 'Complete another scan to compare.' : NO_CHANGES);

  return `
    ${data.saveWarning ? notice(esc(data.saveWarning)) : ''}
    ${freeSpaceMetrics(points)}
    ${card({
      title: 'Storage Over Time',
      subtitle: `${points.length} real scan snapshots · up to ${MAX_POINTS_NOTE} retained`,
      bodyHtml: trendChart(points),
    })}
    ${card({
      title: 'What Changed?',
      subtitle: data.coverageNote,
      bodyHtml: data.changes.map(changeRow).join('') || emptyChanges,
    })}
    ${notice(FOOTNOTE, { info: true })}`;
}
