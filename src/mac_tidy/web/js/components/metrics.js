import { esc, formatSize } from '../core/format.js';
import { bytesInTrash, freeSpace } from '../core/selectors.js';
import { state } from '../core/state.js';

export function metric(label, bytes, note, { highlight = false } = {}) {
  const [value, unit] = formatSize(bytes).split(' ');
  return `
    <div class="metric ${highlight ? 'highlight' : ''}">
      <div class="metric-label">${esc(label)}</div>
      <strong>${value}<small>${unit}</small></strong>
      <small>${esc(note)}</small>
    </div>`;
}

/** Like ``metric``, but shows "Unavailable" when the value could not be measured. */
export function measuredMetric(label, bytes, note) {
  if (bytes !== null && bytes !== undefined) return metric(label, bytes, note);
  return `
    <div class="metric">
      <div class="metric-label">${esc(label)}</div>
      <strong class="unavailable-value">Unavailable</strong>
      <small>${esc(note)}</small>
    </div>`;
}

export const metricRow = (...metricsHtml) => `<div class="metrics">${metricsHtml.join('')}</div>`;

export const freeSpaceMetric = (note) => metric('Available space', freeSpace(), note);

export const trashMetric = (note) => metric(
  'Currently in Trash',
  bytesInTrash(),
  state.cleanup.unverifiedTrashCount ? 'Some Trash statuses could not be verified' : note,
);
