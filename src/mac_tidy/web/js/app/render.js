// Draws the current view into the page shell and handles navigation.

import { candidates, visibleSuggestions } from '../core/selectors.js';
import { resetListState, state } from '../core/state.js';
import { VIEWS } from '../views/index.js';
import { isItemList, listResults } from '../views/item-list.js';
import { reviewCleanupView } from '../views/review-cleanup.js';

export const $ = (selector) => document.querySelector(selector);

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

/** Re-render only the results, so the search field keeps focus. */
export function renderResults() {
  if (state.view === 'approvals') {
    const caret = $('#search')?.selectionStart ?? 0;
    $('#content').innerHTML = reviewCleanupView();
    $('#search').focus();
    $('#search').setSelectionRange(caret, caret);
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
