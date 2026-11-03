import { searchField } from '../components/search-field.js';
import { actionButton, coverageNote, notice, symbol } from '../components/primitives.js';
import { esc, formatSize, sumSizes } from '../core/format.js';
import { friendlyName, isWebpackCache, matchesSearch, shortPath } from '../core/selectors.js';
import { state } from '../core/state.js';

const BUILD_CACHE_ADVICE = 'Generated Webpack build files. Stop build jobs and development servers first. This project may recreate its cache on later builds.';
const APP_CACHE_ADVICE = 'Temporary app or package cache. Quit the owning app first. Some cached or offline content may need downloading again.';

const suggestionCard = (d) => `
  <article class="approval-card">
    <div class="approval-top">
      <span class="cache-symbol">${symbol(isWebpackCache(d) ? 'gearshape' : 'shippingbox')}</span>
      <span class="pill cache">Rebuildable cache</span>
    </div>
    <h2>${esc(friendlyName(d))}</h2>
    <div class="approval-size">${formatSize(d.size)}</div>
    <code>${esc(shortPath(d.path))}</code>
    <p>${isWebpackCache(d) ? BUILD_CACHE_ADVICE : APP_CACHE_ADVICE}</p>
    ${d.partial ? '<p class="partial-label">Partial scan — actual size may be larger.</p>' : ''}
    <div class="approval-actions">
      ${actionButton('Review…', 'review-trash', { arg: `dir:${d.id}`, style: 'button primary' })}
      ${actionButton('Information…', 'details', { arg: `dir:${d.id}`, style: 'linkbutton' })}
      ${actionButton('Skip', 'skip', { arg: d.path, style: 'linkbutton skip' })}
    </div>
  </article>`;

export function reviewCleanupView() {
  const rows = state.cleanup.cards.filter((d) => (state.showSkipped || !state.skipped.has(d.path)) && matchesSearch(d));
  const skippedLabel = `${state.showSkipped ? 'Hide skipped' : 'Show skipped'} (${state.skipped.size})`;

  return `
    <div class="queue-summary">
      <div><b>${rows.length} suggestions</b><span>${formatSize(sumSizes(rows))} of eligible cache · nested locations counted once</span></div>
      ${actionButton(skippedLabel, 'toggle-skipped')}
    </div>
    ${notice('Items move to Trash only after you confirm. Empty Trash yourself to reclaim space. Clearing caches may make the next build or app launch slower.', { info: true })}
    <div class="toolbar">${searchField('Search apps and projects')}</div>
    <div class="approval-grid">
      ${rows.map(suggestionCard).join('') || '<div class="empty card">No matching suggestions. You can inspect more locations in Browse Storage.</div>'}
    </div>
    ${coverageNote()}`;
}
