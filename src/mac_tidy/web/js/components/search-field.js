import { esc } from '../core/format.js';
import { state } from '../core/state.js';

/** The search box; app/events.js listens for input on #search. */
export const searchField = (placeholder, label = 'Search paths') =>
  `<input type="search" id="search" aria-label="${esc(label)}" placeholder="${esc(placeholder)}" value="${esc(state.query)}">`;

/** A dropdown. ``options`` are ``[value, text]``; ``selected`` is compared strictly. */
export function selectField(id, label, options, selected, { disabled = false } = {}) {
  const optionsHtml = options.map(([value, text]) =>
    `<option value="${esc(value)}" ${selected === value ? 'selected' : ''}>${esc(text)}</option>`).join('');
  return `<select id="${id}" aria-label="${esc(label)}" ${disabled ? 'disabled' : ''}>${optionsHtml}</select>`;
}

/** A dropdown with a visible caption. */
export const labelledSelect = (caption, ...selectArgs) =>
  `<label>${esc(caption)} ${selectField(...selectArgs)}</label>`;
