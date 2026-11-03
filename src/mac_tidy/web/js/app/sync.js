// Keeps the page in step with the local server by polling its status.

import { isDialogOpen } from '../components/dialog.js';
import { toast } from '../components/toast.js';
import { api } from '../core/api.js';
import { formatTime } from '../core/format.js';
import { setReport } from '../core/selectors.js';
import { state } from '../core/state.js';
import { $, render } from './render.js';

const POLL_BUSY_MS = 1800;
const POLL_IDLE_MS = 12000;
const POLL_RETRY_MS = 5000;
// Views whose numbers change without a rescan (free space, Trash, history).
const ALWAYS_REFRESHED_VIEWS = ['overview', 'activity', 'space', 'trends'];

let pollTimer;
let insightsLoaded = false;

export async function refreshCleanup() {
  state.cleanup = await api.get('/api/cleanup');
}

export async function refreshInsights() {
  [state.insights, state.trends, state.duplicates, state.space] = await Promise.all([
    api.get('/api/insights'),
    api.get('/api/trends'),
    api.get('/api/duplicates'),
    api.get('/api/space'),
  ]);
  // On the first load, adopt the mode and budget of a search already running or finished.
  if (!insightsLoaded && state.duplicates.mode) {
    state.duplicateMode = state.duplicates.mode;
    if (state.duplicates.budget) state.duplicateBudget = state.duplicates.budget;
  }
  insightsLoaded = true;
}

async function loadReport() {
  setReport(await api.get('/api/report'));
  await refreshCleanup();
  render();
  $('#scantime').textContent = 'Scanned ' + formatTime(state.report.finished);
  await refreshInsights();
  if (!isDialogOpen()) render();
}

function showScanStatus(status) {
  const scanning = status.status === 'scanning';
  $('#progress').style.display = scanning ? 'flex' : 'none';
  $('#rescan').disabled = scanning;
  if (scanning) {
    $('#progresstext').textContent =
      `${(status.filesScanned || 0).toLocaleString()} files · ${status.elapsed || 0}s · ${status.current || 'Preparing'}`;
  }
  if (status.status === 'error') {
    toast('Scan failed: ' + status.message);
    $('#scantime').textContent = 'Scan failed — try rescan';
  }
}

/** Refresh Trash status, free space and insights; re-render only when it is visible or changed. */
async function refreshIdle() {
  const before = state.cleanup;
  const duplicatesBefore = JSON.stringify(state.duplicates);
  await refreshCleanup();
  await refreshInsights();
  const trashChanged = state.cleanup.history.length !== before.history.length
    || state.cleanup.bytesInTrash !== before.bytesInTrash;
  const duplicatesChanged = state.view === 'duplicates' && duplicatesBefore !== JSON.stringify(state.duplicates);
  const visible = ALWAYS_REFRESHED_VIEWS.includes(state.view);
  if (!isDialogOpen() && (trashChanged || visible || duplicatesChanged)) render();
}

const hasNewReport = (status) =>
  status.hasReport && (!state.report || (status.status === 'complete' && state.report.finished !== status.reportFinished));

/** Poll faster while something is running that the user is waiting on. */
const pollDelay = (status) =>
  status.status === 'scanning' || state.duplicates?.status === 'running' || state.space?.status === 'loading'
    ? POLL_BUSY_MS
    : POLL_IDLE_MS;

export async function poll() {
  clearTimeout(pollTimer);
  try {
    const status = await api.get('/api/status');
    showScanStatus(status);
    if (hasNewReport(status)) await loadReport();
    else if (status.status === 'complete' && state.report) await refreshIdle();
    pollTimer = setTimeout(poll, pollDelay(status));
  } catch {
    $('#scantime').textContent = 'Connection lost';
    pollTimer = setTimeout(poll, POLL_RETRY_MS);
  }
}
