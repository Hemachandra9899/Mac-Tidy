import { infoButton, locationRow, sizeOrUnavailable } from '../components/insight-rows.js';
import { actionButton, card, empty, notice } from '../components/primitives.js';
import { labelledSelect } from '../components/search-field.js';
import { esc, formatSize } from '../core/format.js';
import { shortPath } from '../core/selectors.js';
import { state } from '../core/state.js';

const MODES = [['files', 'Files'], ['folders', 'Folders']];
const BUDGETS = [2, 8, 32].map((gigabytes) => [gigabytes * 1e9, `${gigabytes} GB`]);
const INTRO = 'This search reads local file contents only when started. It excludes symlinks, cloud placeholders, app/Photos packages, hidden files, dependency trees and anything inside a code project, where copies are often intentional. File search counts hard links once. No file is removed automatically.';
const IDLE_HELP = 'Start a search to verify exact matches. Similar-looking photos are not treated as identical files. Folder comparisons inspect only complete, size-matched candidates.';
const plural = (count, word) => `${count} ${word}${count === 1 ? '' : 's'}`;

function controls(running) {
  return `
    <div class="toolbar">
      ${labelledSelect('Compare', 'duplicate-mode', 'Compare', MODES, state.duplicateMode, { disabled: running })}
      ${labelledSelect('Read budget', 'duplicate-budget', 'Read budget', BUDGETS, state.duplicateBudget, { disabled: running })}
      ${actionButton(running ? 'Searching…' : 'Find Exact Duplicates', 'find-duplicates', { style: 'button primary', disabled: running })}
      ${running ? actionButton('Cancel', 'cancel-duplicates') : ''}
    </div>`;
}

const folderGroupCard = (group) => card({
  title: `Matching folders · ${formatSize(group.size)} content each`,
  subtitle: 'Relative names, empty directories and full file SHA-256 hashes match. Whole-folder removal is not offered here.',
  bodyHtml: group.folders.map((d) => locationRow(d)).join(''),
});

function copyRow(group, file, keeperIndex) {
  const isKeeper = file.index === keeperIndex;
  const review = !isKeeper && file.trashPolicy?.allowed
    ? actionButton('Review Duplicate…', 'review-duplicate', {
      arg: JSON.stringify({ group: group.id, id: file.index, keeper: keeperIndex }),
      style: 'button',
    })
    : '';
  return `
    <div class="duplicate-file">
      <label>
        <input type="radio" name="keeper-${group.id}" data-keeper-group="${group.id}" value="${file.index}" ${isKeeper ? 'checked' : ''}>
        <span><b>${isKeeper ? 'Keep this copy' : 'Other copy'}</b><code>${esc(shortPath(file.path))}</code></span>
      </label>
      <div class="actions">${infoButton(file.type || 'file', file.index)}${review}</div>
    </div>`;
}

function fileGroupCard(group) {
  const requested = state.duplicateKeepers[group.id] ?? group.keeper;
  const keeper = group.files.some((f) => f.index === requested) ? requested : group.keeper;
  return card({
    title: `${group.files.length} matching copies · ${formatSize(group.size)} each`,
    subtitle: 'Choose the copy to keep. Each other copy still requires its own removal approval.',
    bodyHtml: group.files.map((file) => copyRow(group, file, keeper)).join(''),
  });
}

function skippedNote(result) {
  const notes = [
    `${result.skippedBudget || 0} candidates skipped for the read budget`,
    `${result.skippedChanged || 0} excluded, unreadable or changed candidates`,
  ];
  if (result.skippedProject) {
    notes.push(`${result.skippedProject} inside code projects skipped, because copies there are often intentional`);
  }
  return `<p class="maphint">${esc(result.scope || '')} ${notes.join('; ')}. Results can change as apps modify files.</p>`;
}

function completeResult(result) {
  const folders = result.mode === 'folders';
  const summary = folders
    ? 'Folder groups can overlap; no combined savings estimate.'
    : `${sizeOrUnavailable(result.wasted || 0)} of repeated logical content; actual disk savings may be lower`;
  const groups = result.groups.map(folders ? folderGroupCard : fileGroupCard).join('')
    || empty('No verified duplicates within the chosen scope and budget.');
  return `
    <div class="queue-summary">
      <div><b>${plural(result.groups.length, `verified ${folders ? 'folder' : 'file'} group`)}</b><span>${summary}</span></div>
    </div>
    ${groups}
    ${skippedNote(result)}`;
}

function resultContent(result, stale) {
  if (result.status === 'running') {
    return notice(`<span class="spinner"></span> ${formatSize(result.bytesHashed || 0)} read · search running locally. You can cancel without changing files.`, { info: true });
  }
  if (stale) return notice('The storage report changed. Start a new duplicate search before reviewing removal.');
  if (result.status === 'error') return notice(esc(result.message));
  if (result.status === 'cancelled') return empty('Search cancelled. No files were moved.');
  if (result.status === 'complete') return completeResult(result);
  return card({ bodyHtml: empty(IDLE_HELP) });
}

export function duplicatesView() {
  const result = state.duplicates || { status: 'idle', groups: [] };
  const stale = Boolean(result.revision) && result.revision !== state.report.finished;
  return `
    ${notice(INTRO, { info: true })}
    ${controls(result.status === 'running')}
    ${resultContent(result, stale)}`;
}
