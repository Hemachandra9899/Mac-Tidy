import { esc, formatSize } from '../core/format.js';
import { itemKey, matchesFilter, matchesSearch, shortPath } from '../core/selectors.js';
import { state } from '../core/state.js';
import { actionButton, pill } from './primitives.js';

export const PAGE_SIZE = 100;
const COMPACT_ROWS = 30;

const COLUMNS = [
  ['col-name', 'Name & location'],
  ['col-size', 'Allocated size'],
  ['col-guidance', 'Guidance'],
  ['col-action', 'Action'],
];

const tableRow = (d, type) => `
  <tr>
    <td><b title="${esc(d.name)}">${esc(d.name)}</b><small title="${esc(d.path)}">${esc(shortPath(d.path))}${d.partial ? ' · partial' : ''}</small></td>
    <td>${formatSize(d.size)}</td>
    <td>${pill(d)}</td>
    <td>${actionButton('Review ↗', 'details', { arg: itemKey(type, d), style: 'table-action' })}</td>
  </tr>`;

function table(rows, type) {
  const head = COLUMNS.map(([cls, title]) => `<th class="${cls}">${title}</th>`).join('');
  const body = rows.map((d) => tableRow(d, type)).join('') || '<tr><td colspan="4" class="empty">No items match this view.</td></tr>';
  return `<div class="tablewrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function pager(total, start, end) {
  const range = total ? ` · ${start + 1}–${end}` : '';
  return `
    <div class="toolbar table-pager">
      <span class="maphint">${total.toLocaleString()} results${range}</span>
      ${actionButton('← Previous', 'page', { arg: -1, disabled: state.page === 0 })}
      ${actionButton('Next →', 'page', { arg: 1, disabled: end >= total })}
    </div>`;
}

/** Searchable, filterable, paginated table driven by state.query/filter/page. */
export function itemTable(rows, type) {
  const filtered = rows.filter((d) => matchesFilter(d) && matchesSearch(d));
  const start = state.page * PAGE_SIZE;
  const end = Math.min(start + PAGE_SIZE, filtered.length);
  return table(filtered.slice(start, end), type) + pager(filtered.length, start, end);
}

/** The first rows, unfiltered, for the folder explorer. */
export const compactFileTable = (rows) =>
  `<h2 class="section-title">Largest indexed files directly inside</h2>${table(rows.slice(0, COMPACT_ROWS), 'file')}`;
