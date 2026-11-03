import { infoButton, loading, reviewButton, sizeOrUnavailable } from '../components/insight-rows.js';
import { card, empty, notice } from '../components/primitives.js';
import { labelledSelect, searchField } from '../components/search-field.js';
import { esc, formatDateTime } from '../core/format.js';
import { matchesText, shortPath } from '../core/selectors.js';
import { state } from '../core/state.js';

const MAX_ROWS = 200;
const DEFAULT_INDEX_LIMIT = 10000;
const AGE_OPTIONS = [90, 180, 365, 730].map((days) => [days, `${days} days`]);
const INTRO = 'These files have not been modified recently. A file can still be useful or frequently opened without being modified. Last-opened time is not inferred, and no file is selected for removal automatically.';

const fileRow = (f) => `
  <section class="old-file-row">
    <div class="rowname">
      <b>${esc(f.name)}</b>
      <small title="${esc(f.path)}">${esc(shortPath(f.path))}</small>
      <small>Modified ${formatDateTime(f.mtime)} · ${f.ageDays} days ago</small>
    </div>
    <div>
      <b>${sizeOrUnavailable(f.size)}</b>
      <div class="actions">${infoButton(f.type, f.index)}${reviewButton(f.type, f)}</div>
    </div>
  </section>`;

export function olderView() {
  const data = state.insights?.older;
  if (!data) return loading();
  const rows = data.files.filter((f) => f.ageDays >= state.oldDays && matchesText(f.path, f.name));
  const indexLimit = (state.report.reviewFilesLimit || DEFAULT_INDEX_LIMIT).toLocaleString();

  return `
    ${notice(INTRO, { info: true })}
    <div class="toolbar">
      ${labelledSelect('Unchanged for', 'old-days', 'Unchanged for', AGE_OPTIONS, state.oldDays)}
      ${searchField('Search files and paths', 'Search insights')}
    </div>
    ${card({
      title: `${rows.length.toLocaleString()} older files`,
      subtitle: `${data.indexedFiles.toLocaleString()} indexed personal files considered. Largest matches shown first.`,
      bodyHtml: rows.slice(0, MAX_ROWS).map(fileRow).join('') || empty('No indexed files match this age and search.'),
    })}
    <p class="maphint">${esc(data.scope)} A fresh scan indexes up to ${indexLimit} personal files of at least 1 MB.</p>`;
}
