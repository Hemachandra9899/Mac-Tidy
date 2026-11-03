// Small presentational building blocks shared by every view.
// Arguments named *Html are trusted markup; everything else is escaped.

import { esc } from '../core/format.js';
import { state } from '../core/state.js';

export const CHART_COLORS = ['#299b50', '#75bb89', '#a7d1b3', '#6f8d7d', '#b8d5c1', '#cbd4ce', '#e1e6e2'];

export const chartColor = (i) => CHART_COLORS[i % CHART_COLORS.length];

/** An SF Symbol exported to /icons, drawn as a CSS mask so it follows text color. */
export const symbol = (name) =>
  `<span class="sf" aria-hidden="true" style="--symbol:url('/icons/${name}.png')"></span>`;

export const pill = (d) => `<span class="pill ${esc(d.kind)}">${esc(d.label)}</span>`;

/** A button wired to an entry in app/actions.js. */
export function actionButton(label, action, { arg, style = 'button', id, disabled = false } = {}) {
  const attrs = [
    `class="${style}"`,
    `data-action="${action}"`,
    arg !== undefined ? `data-arg="${esc(arg)}"` : '',
    id ? `id="${id}"` : '',
    disabled ? 'disabled' : '',
  ].filter(Boolean).join(' ');
  return `<button ${attrs}>${label}</button>`;
}

export const linkTo = (label, view) => actionButton(label, 'go', { arg: view, style: 'linkbutton' });

export const notice = (html, { info = false } = {}) => `<div class="notice ${info ? 'info' : ''}">${html}</div>`;

export const empty = (text) => `<div class="empty">${esc(text)}</div>`;

export function cardHead(title, subtitle = '', asideHtml = '') {
  return `
    <div class="card-head">
      <div><h2>${esc(title)}</h2>${subtitle ? `<p>${esc(subtitle)}</p>` : ''}</div>
      ${asideHtml}
    </div>`;
}

/** A titled card. ``bodyHtml`` is placed under the heading. */
export const card = ({ title, subtitle, asideHtml, bodyHtml, id }) => `
  <div class="card"${id ? ` id="${id}"` : ''}>
    ${title ? cardHead(title, subtitle, asideHtml) : ''}
    ${bodyHtml}
  </div>`;

export const coverageNote = () => notice(
  `◎ &nbsp; ${state.report.errorsCount.toLocaleString()} locations could not be read. Totals for affected folders are lower bounds.
   ${linkTo('View Scan Details…', 'coverage')}`,
  { info: true },
);
