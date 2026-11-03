// The single source of UI state. Views read it; app/ modules change it.

const SKIPPED_KEY = 'storage-lens-skipped';

function loadSkipped() {
  try {
    return new Set(JSON.parse(localStorage.getItem(SKIPPED_KEY) || '[]'));
  } catch {
    return new Set();
  }
}

export const state = {
  report: null,
  cleanup: { cards: [], history: [] },
  view: 'overview',
  folder: null,
  query: '',
  filter: 'all',
  page: 0,
  selected: null,
  approval: null,
  showSkipped: false,
  skipped: loadSkipped(),
};

export function resetListState() {
  Object.assign(state, { page: 0, query: '', filter: 'all' });
}

export function skipSuggestion(path) {
  state.skipped.add(path);
  try {
    localStorage.setItem(SKIPPED_KEY, JSON.stringify([...state.skipped]));
  } catch {
    // Storage can be unavailable (private window); skipping still works this session.
  }
}
