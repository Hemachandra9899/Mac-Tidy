import { esc, formatSize } from '../core/format.js';
import { itemKey, shortPath } from '../core/selectors.js';
import { symbol } from './primitives.js';

/** A clickable folder with a size bar scaled against ``max``. */
export function folderRow(d, max) {
  const width = Math.max(1, (d.size / (max || 1)) * 100);
  return `
    <div class="folderrow" tabindex="0" role="button" data-action="details" data-arg="${itemKey('dir', d)}">
      <span class="foldericon">${symbol('folder')}</span>
      <div class="rowname">
        <b>${esc(d.name)}</b>
        <small>${esc(shortPath(d.path))}${d.partial ? ' · partial scan' : ''}</small>
      </div>
      <div class="rowsize">${formatSize(d.size)}<div class="tinybar"><span style="width:${width}%"></span></div></div>
      <span class="arrow">${symbol('chevron.right')}</span>
    </div>`;
}

/** Rows scaled against the largest one, or ``emptyHtml`` when there are none. */
export const folderRows = (rows, emptyHtml, max = rows[0]?.size) =>
  rows.map((d) => folderRow(d, max)).join('') || emptyHtml;
