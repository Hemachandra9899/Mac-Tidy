// User actions, keyed by the data-action attribute in the markup.
// Each handler receives the element's data-arg and the element itself.

import { api } from '../core/api.js';
import { closeDialog, showDetails, showTrashReview } from '../components/dialog.js';
import { toast } from '../components/toast.js';
import { itemFor } from '../core/selectors.js';
import { skipSuggestion, state } from '../core/state.js';
import { $, go, render, renderResults } from './render.js';
import { poll, refreshCleanup } from './sync.js';

const MOBILE_WIDTH = 560;

const selectedItem = () => ({ type: state.selected.type, id: state.selected.id, path: state.selected.item.path });

async function reviewTrash(key) {
  const selected = itemFor(key);
  state.selected = selected;
  state.approval = await api.post('/api/trash/preview', { type: selected.type, id: selected.id, path: selected.item.path });
  showTrashReview(selected, state.approval);
}

async function approveTrash(_arg, button) {
  if (!$('#approve-check').checked) return;
  button.disabled = true;
  button.textContent = 'Moving to Trash…';
  try {
    const result = await api.post('/api/trash/approve', { approval: state.approval.approval, confirmed: true });
    closeDialog();
    state.approval = null;
    await refreshCleanup();
    render();
    toast(result.item.warning || 'Moved to Trash. Recover it from Activity. Free space changes when Trash is emptied.');
  } catch (error) {
    // The approval is single-use, so a failed attempt always needs a fresh review.
    button.textContent = 'Move to Trash';
    throw error;
  }
}

function exportReport() {
  const blob = new Blob([JSON.stringify(state.report, null, 2)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'mac-tidy-report.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

export const ACTIONS = {
  go,
  'open-folder': (id) => { state.folder = id === 'root' ? null : Number(id); render(); },
  explore: (id) => { state.folder = Number(id); closeDialog(); go('explorer'); },
  details: (key) => {
    const selected = itemFor(key);
    if (!selected) return;
    state.selected = selected;
    showDetails(selected);
  },
  'review-trash': reviewTrash,
  'approve-trash': approveTrash,
  'close-dialog': closeDialog,
  skip: (path) => { skipSuggestion(path); render(); },
  'toggle-skipped': () => { state.showSkipped = !state.showSkipped; render(); },
  page: (delta) => { state.page += Number(delta); renderResults(); },
  export: exportReport,
  'toggle-sidebar': () => {
    document.body.classList.toggle(innerWidth <= MOBILE_WIDTH ? 'sidebar-open' : 'sidebar-collapsed');
  },
  'copy-path': async () => {
    await navigator.clipboard.writeText(state.selected.item.path);
    toast('Path copied. Finder → Go → Go to Folder (⇧⌘G).');
  },
  reveal: async (_arg, button) => {
    button.disabled = true;
    await api.post('/api/reveal', selectedItem());
    button.disabled = false;
    toast('Opened Finder with this item selected.');
  },
  'reveal-activity': async (id) => {
    await api.post('/api/activity/reveal', { id });
    toast('Opened the item in Trash. Use Finder’s Put Back command to recover it.');
  },
  rescan: async (_arg, button) => {
    button.disabled = true;
    await api.post('/api/rescan', {});
    toast('Fresh scan started.');
    poll();
  },
};
