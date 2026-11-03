// "All Candidates" and "Large Files": the same searchable table over different rows.

import { itemTable } from '../components/item-table.js';
import { searchField, selectField } from '../components/search-field.js';
import { actionButton, card, coverageNote, notice } from '../components/primitives.js';
import { candidates } from '../core/selectors.js';
import { state } from '../core/state.js';

const FILTERS = [
  ['all', 'All categories'],
  ['cache', 'Rebuildable cache'],
  ['logs', 'Logs'],
  ['downloads', 'Downloads'],
  ['developer', 'Developer data'],
  ['backup', 'Backups'],
  ['review', 'Keep unless unneeded'],
  ['system', 'Managed files'],
];

const LISTS = {
  cleanup: {
    rows: candidates,
    type: 'dir',
    introHtml: notice('Review candidates are not a deletion recommendation for the entire folder. Cache contents can regenerate; backups, downloads and developer data may be valuable. For package caches, prefer the package manager’s own cleanup command.'),
  },
  files: {
    rows: () => state.report.files,
    type: 'file',
    introHtml: notice('The 1,500 largest readable files by allocated disk bytes. Sparse files also show their logical size in details. File contents were not read; duplicates have not been identified.', { info: true }),
  },
};

/** Table only, for re-rendering results without replacing the search field. */
export function listResults(view) {
  const list = LISTS[view];
  return itemTable(list.rows(), list.type);
}

export const isItemList = (view) => view in LISTS;

export function itemListView(view) {
  return `
    ${LISTS[view].introHtml}
    <div class="toolbar">
      ${searchField('Search by file, app or folder path…')}
      ${selectField('filter', 'Filter by guidance', FILTERS, state.filter)}
      ${actionButton('Export scan JSON ↓', 'export')}
    </div>
    ${card({ id: 'results', bodyHtml: listResults(view) })}
    ${coverageNote()}`;
}
