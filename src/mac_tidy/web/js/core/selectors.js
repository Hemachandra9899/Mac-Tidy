// Derived data over the loaded report and cleanup state. No DOM access.

import { sortBySize } from './format.js';
import { state } from './state.js';

const CANDIDATE_KINDS = ['cache', 'logs', 'downloads', 'developer', 'backup'];
const MIN_CANDIDATE_BYTES = 1e6;
const MIN_MANAGED_BYTES = 1e9;

const FRIENDLY_NAMES = {
  _cacache: 'npm download cache',
  Google: 'Google / Chrome cache',
  Yarn: 'Yarn package cache',
  BraveSoftware: 'Brave browser cache',
  'com.brave.Browser': 'Brave app cache',
  'com.microsoft.VSCode.ShipIt': 'VS Code updater cache',
  'ms-playwright': 'Playwright browser downloads',
  Homebrew: 'Homebrew download cache',
};

let candidateCache = null;

export function setReport(report) {
  report.files.forEach((file, index) => { file.index = index; });
  state.report = report;
  candidateCache = null;
}

// Items

export const dirs = () => state.report.dirs;

export const childrenOf = (id) => sortBySize(dirs().filter((d) => d.parent === id));

/** The "type:id" key used in data-arg attributes to refer to a scanned item. */
export const itemKey = (type, d) => `${type}:${type === 'dir' ? d.id : d.index}`;

export function itemFor(key) {
  const [type, rawId] = key.split(':');
  const id = Number(rawId);
  const item = type === 'dir' ? dirs()[id] : state.report.files[id];
  return item ? { type, id, item } : null;
}

export function shortPath(path) {
  const home = state.report?.home;
  return home && path.startsWith(home) ? '~' + path.slice(home.length) : path;
}

export const isWebpackCache = (d) => d.path.includes('/node_modules/.cache/webpack');

export function friendlyName(d) {
  if (FRIENDLY_NAMES[d.name]) return FRIENDLY_NAMES[d.name];
  if (isWebpackCache(d)) return `${d.path.split('/node_modules/')[0].split('/').pop()} build cache`;
  return `${d.name} cache`;
}

// Filtering

export function matchesSearch(d) {
  const query = state.query.toLowerCase();
  return !query || d.path.toLowerCase().includes(query);
}

export const matchesFilter = (d) => state.filter === 'all' || d.kind === state.filter;

// Collections

/** Reviewable folders, excluding any nested inside a folder of the same kind. */
export function candidates() {
  if (candidateCache) return candidateCache;
  const all = dirs();
  candidateCache = sortBySize(all.filter((d) => {
    if (!CANDIDATE_KINDS.includes(d.kind) || d.size < MIN_CANDIDATE_BYTES) return false;
    for (let parent = d.parent; parent !== null; parent = all[parent].parent) {
      if (all[parent].kind === d.kind && all[parent].size >= MIN_CANDIDATE_BYTES) return false;
    }
    return true;
  }));
  return candidateCache;
}

/** Top-level app data folders over 1 GB in Application Support and Containers. */
export function managedAppData(limit = 3) {
  const home = state.report.home;
  const bases = [`${home}/Library/Application Support/`, `${home}/Library/Containers/`];
  const isDirectChild = (d) => bases.some((base) => d.path.startsWith(base) && !d.path.slice(base.length).includes('/'));
  return sortBySize(dirs().filter((d) => d.size > MIN_MANAGED_BYTES && isDirectChild(d))).slice(0, limit);
}

export const visibleSuggestions = () => state.cleanup.cards.filter((d) => !state.skipped.has(d.path));

// Space

export const freeSpace = () => state.cleanup.diskFree ?? state.report.disk.free;

export const bytesInTrash = () => state.cleanup.bytesInTrash ?? 0;
