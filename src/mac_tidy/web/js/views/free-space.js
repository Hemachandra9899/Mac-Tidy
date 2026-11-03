import { sizeOrUnavailable } from '../components/insight-rows.js';
import { measuredMetric, metric, metricRow } from '../components/metrics.js';
import { card, empty, notice, numberedSteps } from '../components/primitives.js';
import { esc, formatDateTime } from '../core/format.js';
import { state } from '../core/state.js';

const SNAPSHOT_HELP = 'https://support.apple.com/en-us/102154';
const CAPACITY_API = 'https://developer.apple.com/documentation/foundation/urlresourcevalues/volumeavailablecapacityforimportantusage';
const isMissing = (value) => value === null || value === undefined;

function explanations(data) {
  const trash = isMissing(data.trashBytes)
    ? 'Trash size could not be read.'
    : `${sizeOrUnavailable(data.trashBytes)} measured in this user’s Trash.`;
  return numberedSteps([
    ['Trash still occupies storage', `${trash} Moving files to Trash is reversible; space is generally reclaimed only after you empty it yourself.`],
    ['macOS can reclaim some capacity', '“Available for important use” is an operating-system estimate, not a list of disposable files. Snapshots, caches and storage reservations affect the difference.'],
    ['Copies can share APFS blocks', 'Equal file content or large logical file sizes do not guarantee that deleting one copy will free the displayed number of bytes.'],
  ]);
}

function snapshotsCard(snapshots) {
  const known = Boolean(snapshots);
  const list = snapshots?.length
    ? `<ul class="snapshot-list">${snapshots.map((name) => `<li><code>${esc(name)}</code></li>`).join('')}</ul>`
    : empty('No local Time Machine snapshot names were returned, or access is unavailable.');
  return card({
    title: 'Local Time Machine Snapshots',
    subtitle: known ? `${snapshots.length} names reported; sizes are not measured` : 'Snapshot names unavailable',
    bodyHtml: list,
  });
}

export function spaceView() {
  const data = state.space || {};
  const { capacity } = data;
  const checked = data.checkedAt
    ? `<p class="maphint">Checked ${formatDateTime(data.checkedAt)}. Estimates refresh at most once per minute.</p>`
    : '';

  return `
    ${data.status === 'loading' ? notice('Refreshing macOS space estimates and local snapshot names…', { info: true }) : ''}
    ${metricRow(
      metric('Filesystem free', capacity?.free ?? state.cleanup.diskFree, 'Space reported available now'),
      measuredMetric('Available for important use', capacity?.freeIncludingPurgeable,
        capacity ? 'Native macOS estimate; includes reclaimable capacity' : 'Native estimate unavailable'),
      measuredMetric('Potentially reclaimable', data.purgeable,
        isMissing(data.purgeable) ? 'Estimate unavailable' : 'Difference between macOS capacity estimates'),
    )}
    ${card({ title: 'Why the Numbers Differ', bodyHtml: explanations(data) + checked })}
    ${snapshotsCard(data.snapshots)}
    <p class="maphint">Mac Tidy does not delete snapshots or empty Trash.
      <a href="${SNAPSHOT_HELP}" target="_blank" rel="noreferrer">Apple’s snapshot explanation ↗</a> ·
      <a href="${CAPACITY_API}" target="_blank" rel="noreferrer">Native capacity API ↗</a></p>`;
}
