// The shared <dialog>: item information, and the Move to Trash confirmation.

import { esc, formatDateTime, formatSize } from '../core/format.js';
import { friendlyName, itemKey } from '../core/selectors.js';
import { actionButton, notice, pill, symbol } from './primitives.js';

const dialog = () => document.querySelector('#details');
const content = () => document.querySelector('#detailcontent');

function show(mode, html) {
  dialog().dataset.mode = mode;
  content().innerHTML = html;
  if (!dialog().open) dialog().showModal();
}

export const isDialogOpen = () => dialog().open;

export const closeDialog = () => dialog().close();

/** Show a status line inside the open dialog, where a toast would be hidden by the backdrop. */
export function setDialogStatus(message) {
  let status = document.querySelector('#dialog-status');
  if (!status) {
    status = document.createElement('p');
    status.id = 'dialog-status';
    status.setAttribute('role', 'status');
    content().append(status);
  }
  status.textContent = message;
}

function detailMeta(d) {
  return [
    'Allocated size',
    d.partial ? ' · Partial scan; actual size may be larger' : '',
    d.logical !== undefined ? ` · Logical file size: ${formatSize(d.logical)}` : '',
    `<br>Modified ${formatDateTime(d.mtime)}`,
  ].join('');
}

export function showDetails({ type, id, item: d }) {
  const policyNote = d.trashPolicy?.allowed
    ? 'You can review this exact item before moving it to Trash. It remains recoverable until you empty Trash.'
    : esc(d.trashPolicy?.reason || 'Manage this item in Finder or its owning app.');

  show('detail', `
    <h2 id="detail-title">${esc(d.name)}</h2>
    ${pill(d)}
    <div class="bigsize">${formatSize(d.size)}</div>
    <code>${esc(d.path)}</code>
    <div class="detailmeta">${detailMeta(d)}</div>
    <p>${esc(d.advice)}</p>
    ${notice(policyNote, { info: true })}
    <div class="actions">
      ${actionButton('Show in Finder', 'reveal')}
      ${actionButton('Copy Path', 'copy-path')}
      ${type === 'dir' ? actionButton('Open Folder', 'explore', { arg: id }) : ''}
      ${d.trashPolicy?.allowed ? actionButton('Review Removal…', 'review-trash', { arg: itemKey(type, d), style: 'button danger' }) : ''}
    </div>`);
}

export function showTrashReview({ item: d, type }, plan) {
  const isCache = d.kind === 'cache';
  const acknowledgement = isCache || d.kind === 'logs'
    ? 'I’ve stopped this app, its builds and any active render jobs.'
    : type==='dir' ? 'I’ve reviewed this folder, stopped jobs using it, and understand how to recreate it.' : 'I’ve reviewed this file and no longer need it here.';

  show('approval', `
    <div class="mac-alert-icon">${symbol('trash')}</div>
    <h2 id="detail-title">Move “${esc(isCache ? friendlyName(d) : d.name)}” to Trash?</h2>
    <p class="alert-message">This item will stay in Trash until you empty it. You can find it again in Activity & Recovery.</p>
    <div class="alert-summary"><span>${isCache ? 'Rebuildable cache' : 'Item size'}</span><b>${formatSize(plan.size)}</b></div>
    <code>${esc(plan.path)}</code>
    <p class="inline-help trash-advice">${esc(plan.advice)}</p>${plan.keeper?`<p class="inline-help">Copy to keep:<code>${esc(plan.keeper)}</code>It must still exist and remain unchanged when you approve.</p>`:""}
    <label class="approval-checkbox"><input id="approve-check" type="checkbox"><span>${acknowledgement}</span></label>
    <div class="actions">
      ${actionButton('Show in Finder', 'reveal', { style: 'linkbutton' })}
      ${actionButton('Cancel', 'close-dialog', { id: 'cancel-trash' })}
      ${actionButton('Move to Trash', 'approve-trash', { id: 'approve-trash', style: 'button danger', disabled: true })}
    </div>
    <p class="maphint">Approval expires after 5 minutes. Changed items require a new review.</p>`);
  document.querySelector('#cancel-trash').focus();
}
