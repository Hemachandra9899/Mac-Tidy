// Rows shared by the insight views (apps, developer, older files, duplicates, trends).

import { esc, formatSize } from '../core/format.js';
import { shortPath } from '../core/selectors.js';
import { actionButton } from './primitives.js';
import { searchField } from './search-field.js';

/** A size, or "Unavailable" when it could not be measured. */
export const sizeOrUnavailable = (bytes) =>
  bytes === null || bytes === undefined ? 'Unavailable' : formatSize(bytes);

export const loading = () =>
  '<div class="loading-card"><span class="spinner"></span>Preparing storage insights…</div>';

export const infoButton = (type, id) =>
  actionButton('Information…', 'details', { arg: `${type}:${id}`, style: 'linkbutton' });

/** "Review Removal…" when the item may be moved to Trash, otherwise a plain label. */
export const reviewButton = (type, row) => row.trashPolicy?.allowed
  ? actionButton('Review Removal…', 'review-trash', { arg: `${type}:${row.id ?? row.index}`, style: 'button' })
  : '<span class="pill">Manage in owning app</span>';

/** A folder or file with its size and an Information link. */
export function locationRow(d, type = 'dir') {
  const name = d.name || d.label || d.path.split('/').pop();
  return `
    <div class="insight-location">
      <div class="rowname">
        <b>${esc(name)}</b>
        <small title="${esc(d.path)}">${esc(shortPath(d.path))}${d.partial ? ' · partial' : ''}</small>
      </div>
      <b class="insight-size">${sizeOrUnavailable(d.size)}</b>
      ${infoButton(type, d.id ?? d.index)}
    </div>`;
}

/** A titled entry with a size, a path and actions, used in lists of tools and projects. */
export function toolRow({ title, subtitle, size, path, extraHtml = '', actionsHtml }) {
  return `
    <section class="tool-row">
      <div class="card-head">
        <div><h3>${esc(title)}</h3><p>${esc(subtitle)}</p></div>
        <b>${sizeOrUnavailable(size)}</b>
      </div>
      <code class="insight-path">${esc(shortPath(path))}</code>
      ${extraHtml}
      <div class="actions">${actionsHtml}</div>
    </section>`;
}

/** The search box used on insight screens. */
export const insightSearch = () =>
  `<div class="toolbar">${searchField('Search names and locations', 'Search insights')}</div>`;
