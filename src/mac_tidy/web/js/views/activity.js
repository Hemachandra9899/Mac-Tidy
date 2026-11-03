import { freeSpaceMetric, metricRow, trashMetric } from '../components/metrics.js';
import { actionButton, card, empty, notice } from '../components/primitives.js';
import { esc, formatDateTime, formatSize } from '../core/format.js';
import { shortPath } from '../core/selectors.js';
import { state } from '../core/state.js';

const activityRow = (d) => `
  <div class="activity-row">
    <span class="activity-check">✓</span>
    <div class="rowname">
      <b>${esc(d.path.split('/').pop())}</b>
      <small title="${esc(d.path)}">${esc(shortPath(d.path))}</small>
      <small>${formatDateTime(d.time)} · ${esc(d.statusLabel || 'Status unavailable')} · ${formatSize(d.size)}</small>
    </div>
    ${actionButton('Show in Trash', 'reveal-activity', { arg: d.id, disabled: d.status === 'not_in_trash' })}
  </div>`;

export function activityView() {
  const { history } = state.cleanup;
  return `
    ${metricRow(
      trashMetric(`${history.length} approved actions in history`),
      freeSpaceMetric('Filesystem space, not estimated savings'),
    )}
    ${notice('Moving an item to Trash keeps it recoverable and usually does not free disk space. To recover, reveal it in Trash and use Finder’s Put Back command. Empty Trash yourself only when certain, then rescan.', { info: true })}
    ${card({
      title: 'Your cleanup activity',
      subtitle: 'Only completed moves appear here. Saved locally on this Mac.',
      bodyHtml: history.map(activityRow).join('') || empty('No approved removals yet. Review a suggestion in Review Cleanup to get started.'),
    })}`;
}
