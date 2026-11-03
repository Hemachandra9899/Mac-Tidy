// Page-wide event delegation: one listener per event type.

import { toast } from '../components/toast.js';
import { state } from '../core/state.js';
import { VIEWS } from '../views/index.js';
import { ACTIONS } from './actions.js';
import { $, go, renderResults } from './render.js';

async function onClick(event) {
  const element = event.target.closest('[data-action]');
  const action = element && ACTIONS[element.dataset.action];
  if (!action) return;
  try {
    await action(element.dataset.arg, element);
  } catch (error) {
    toast(error.message);
    // A failed approval is single-use and stays disabled until the item is reviewed again.
    if (element.dataset.action !== 'approve-trash') element.disabled = false;
  }
}

function onKeydown(event) {
  const { target } = event;
  if (target.matches('[role=button][data-action]') && ['Enter', ' '].includes(event.key)) {
    event.preventDefault();
    target.click();
  }
}

function onInput(event) {
  if (event.target.id !== 'search') return;
  state.query = event.target.value;
  state.page = 0;
  renderResults();
}

// Handlers for form controls, keyed by element id.
const CHANGE_HANDLERS = {
  'approve-check': (el) => { $('#approve-trash').disabled = !el.checked; },
  filter: (el) => { state.filter = el.value; state.page = 0; renderResults(); },
  'old-days': (el) => { state.oldDays = Number(el.value); renderResults(); },
  'stale-only': (el) => { state.staleOnly = el.checked; renderResults(); },
  'duplicate-mode': (el) => { state.duplicateMode = el.value; },
  'duplicate-budget': (el) => { state.duplicateBudget = Number(el.value); },
};

function onChange(event) {
  const element = event.target;
  if (element.dataset.keeperGroup) {
    state.duplicateKeepers[element.dataset.keeperGroup] = Number(element.value);
    renderResults();
  } else {
    CHANGE_HANDLERS[element.id]?.(element);
  }
}

function onHashChange() {
  const next = location.hash.slice(1);
  if (VIEWS[next] && state.view !== next) go(next);
}

export function bindEvents() {
  document.addEventListener('click', onClick);
  document.addEventListener('keydown', onKeydown);
  document.addEventListener('input', onInput);
  document.addEventListener('change', onChange);
  window.addEventListener('hashchange', onHashChange);
}
