// Keeps the page in step with the local server by polling its status.

import { toast } from '../components/toast.js';
import { isDialogOpen } from '../components/dialog.js';
import { api } from '../core/api.js';
import { formatTime } from '../core/format.js';
import { setReport } from '../core/selectors.js';
import { state } from '../core/state.js';
import { $, render } from './render.js';

const POLL_SCANNING_MS = 1800;
const POLL_IDLE_MS = 12000;
const POLL_RETRY_MS = 5000;
const ALWAYS_REFRESHED_VIEWS = ['overview', 'activity', 'space', 'trends'];

let pollTimer;

export async function refreshCleanup() {
  state.cleanup = await api.get('/api/cleanup');
}

export async function refreshInsights() {
  [state.insights,state.trends,state.duplicates,state.space] = await Promise.all([
    api.get('/api/insights'),api.get('/api/trends'),api.get('/api/duplicates'),api.get('/api/space'),
  ]);
}
async function loadReport() {
  setReport(await api.get('/api/report'));
  await refreshCleanup();
  render();
  $('#scantime').textContent = 'Scanned ' + formatTime(state.report.finished);
  await refreshInsights();
  if(!isDialogOpen())render();
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

/** Refresh Trash status and free space; re-render only when it is visible or changed. */
async function refreshIdle() {
  const before = state.cleanup;
  const previousDuplicates=JSON.stringify(state.duplicates);
  await refreshCleanup();
  await refreshInsights();
  const changed = state.cleanup.history.length !== before.history.length
    || state.cleanup.bytesInTrash !== before.bytesInTrash;
  if (!isDialogOpen() && (changed || ALWAYS_REFRESHED_VIEWS.includes(state.view) || (state.view==='duplicates'&&previousDuplicates!==JSON.stringify(state.duplicates)))) render();
}

const hasNewReport = (status) =>
  status.hasReport && (!state.report || (status.status === 'complete' && state.report.finished !== status.reportFinished));

export async function poll() {
  clearTimeout(pollTimer);
  try {
    const status = await api.get('/api/status');
    showScanStatus(status);
    if (hasNewReport(status)) await loadReport();
    else if (status.status === 'complete' && state.report) await refreshIdle();
    pollTimer = setTimeout(poll, status.status === 'scanning' || state.duplicates?.status==='running' || state.space?.status==='loading' ? POLL_SCANNING_MS : POLL_IDLE_MS);
  } catch {
    $('#scantime').textContent = 'Connection lost';
    pollTimer = setTimeout(poll, POLL_RETRY_MS);
  }
}
