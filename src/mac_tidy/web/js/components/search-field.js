import { esc } from '../core/format.js';
import { state } from '../core/state.js';

/** The search box; app/events.js listens for input on #search. */
export const searchField = (placeholder) =>
  `<input type="search" id="search" aria-label="Search paths" placeholder="${esc(placeholder)}" value="${esc(state.query)}">`;

export function selectField(id, label, options, selected) {
  const optionsHtml = options.map(([value, text]) =>
    `<option value="${esc(value)}" ${selected === value ? 'selected' : ''}>${esc(text)}</option>`).join('');
  return `<select id="${id}" aria-label="${esc(label)}">${optionsHtml}</select>`;
}
