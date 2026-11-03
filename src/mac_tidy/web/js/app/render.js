// Draws the current view into the page shell and handles navigation.

import { candidates, visibleSuggestions } from '../core/selectors.js';
import { resetListState, state } from '../core/state.js';
import { VIEWS } from '../views/index.js';
import { isItemList, listResults } from '../views/item-list.js';
import { reviewCleanupView } from '../views/review-cleanup.js';

export const $ = (selector) => document.querySelector(selector);

// Views redrawn whole when a filter changes, because their results sit beside other content.
const INSIGHT_VIEWS = ['apps', 'developer', 'older', 'duplicates'];

export function render() {
  if (!state.report) return;
  const view = VIEWS[state.view];
  $('#pagetitle').textContent = view.title;
  $('#pagesubtitle').textContent = view.subtitle;
  $('#pagecrumb').textContent = view.crumb;
  document.querySelectorAll('nav button').forEach((b) => b.classList.toggle('active', b.dataset.arg === state.view));
  $('#navcount').textContent = candidates().length;
  $('#approve-count').textContent = visibleSuggestions().length;
  $('#activity-count').textContent = state.cleanup.history.length;
  $('#content').innerHTML = view.render();
}

/** Replace the page content, keeping focus and caret in the search field. */
function replaceContent(html, { alwaysFocus = false } = {}) {
  const input = $('#search');
  const refocus = alwaysFocus || input === document.activeElement;
  const caret = input?.selectionStart ?? 0;
  $('#content').innerHTML = html;
  const search = $('#search');
  if (refocus && search) {
    search.focus();
    search.setSelectionRange(caret, caret);
  }
}

/** Re-render only what a search or filter changed. */
export function renderResults() {
  if (INSIGHT_VIEWS.includes(state.view)) {
    replaceContent(VIEWS[state.view].render());
  } else if (state.view === 'approvals') {
    replaceContent(reviewCleanupView(), { alwaysFocus: true });
  } else if (isItemList(state.view)) {
    $('#results').innerHTML = listResults(state.view);
  }
}

export function go(view) {
  document.body.classList.remove('sidebar-open');
  state.view = view;
  resetListState();
  location.hash = view;
  render();
  window.scrollTo(0, 0);
}
