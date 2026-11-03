import { folderRows } from '../components/folder-row.js';
import { compactFileTable } from '../components/item-table.js';
import { actionButton, card, chartColor, coverageNote, empty, notice } from '../components/primitives.js';
import { esc, formatSize, sumSizes } from '../core/format.js';
import { childrenOf, dirs, itemKey, shortPath } from '../core/selectors.js';
import { state } from '../core/state.js';

const TREEMAP_TILES = 12;
const MIN_TILE_PERCENT = 13;
const TILE_SPAN_PERCENT = 85;
const MAX_ROWS = 200;

const openFolder = (label, id) => actionButton(label, 'open-folder', { arg: id });

function breadcrumbs(current) {
  const trail = [];
  for (let d = current; d; d = d.parent === null ? null : dirs()[d.parent]) trail.unshift(d);
  const crumbs = trail.map((d) => `<span>/</span>${openFolder(esc(d.name), d.id)}`).join('');
  return `<div class="breadcrumbs">${openFolder('All scanned locations', 'root')}${crumbs}</div>`;
}

function treemap(children) {
  const top = children.slice(0, TREEMAP_TILES);
  const total = sumSizes(top) || 1;
  const tiles = top.map((d, i) => `
    <button class="tile" data-action="open-folder" data-arg="${d.id}"
      style="background:${chartColor(i)};flex-basis:${Math.max(MIN_TILE_PERCENT, (d.size / total) * TILE_SPAN_PERCENT)}%">
      <b>${esc(d.name)}</b>
      <div><strong>${formatSize(d.size)}</strong><br><small>${d.partial ? 'Partial measurement' : 'Explore folder'} ↘</small></div>
    </button>`).join('');
  return card({
    title: 'Follow the space',
    subtitle: `Click a block to drill into that folder. Largest ${TREEMAP_TILES} indexed subfolders shown (1 MB minimum).`,
    asideHtml: `<span class="pill">${children.length} subfolders</span>`,
    bodyHtml: `
      <div class="treemap">${tiles || '<p class="empty">No measured subfolders. Files may live directly in this folder.</p>'}</div>
      <p class="maphint">Blocks use a minimum width for readability; sizes are labeled. Files directly in the parent folder are not blocks.</p>`,
  });
}

const currentFolderNotice = (d) => !d ? '' : notice(
  `${esc(shortPath(d.path))} · ${formatSize(d.size)}${d.partial ? ' · Partial coverage' : ''}
   ${actionButton('Review this folder ↗', 'details', { arg: itemKey('dir', d), style: 'linkbutton' })}`,
  { info: true },
);

export function explorerView() {
  const current = state.folder === null ? null : dirs()[state.folder];
  const children = childrenOf(state.folder).filter((d) => d.size > 0);
  const files = current ? state.report.files.filter((f) => f.parent === current.id) : [];

  return `
    ${breadcrumbs(current)}
    ${currentFolderNotice(current)}
    ${treemap(children)}
    ${card({
      title: `Inside ${current?.name || 'this Mac'}`,
      subtitle: 'Folder rows open details and Finder actions.',
      bodyHtml: folderRows(children.slice(0, MAX_ROWS), empty('No measured subfolders.')) + (current ? compactFileTable(files) : ''),
    })}
    ${coverageNote()}`;
}
