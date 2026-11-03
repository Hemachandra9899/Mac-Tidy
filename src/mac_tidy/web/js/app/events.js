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

function onChange(event) {
  if (event.target.id === 'old-days') { state.oldDays=Number(event.target.value);renderResults();
  } else if(event.target.id==='stale-only'){state.staleOnly=event.target.checked;renderResults();
  } else if(event.target.id==='duplicate-mode'){state.duplicateMode=event.target.value;
  } else if(event.target.id==='duplicate-budget'){state.duplicateBudget=Number(event.target.value);
  } else if(event.target.dataset.keeperGroup){state.duplicateKeepers[event.target.dataset.keeperGroup]=Number(event.target.value);renderResults();
  } else if (event.target.id === 'approve-check') {
    $('#approve-trash').disabled = !event.target.checked;
  } else if (event.target.id === 'filter') {
    state.filter = event.target.value;
    state.page = 0;
    renderResults();
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
