import { insightSearch, infoButton, loading, locationRow, sizeOrUnavailable } from '../components/insight-rows.js';
import { card, empty, notice } from '../components/primitives.js';
import { esc } from '../core/format.js';
import { matchesText } from '../core/selectors.js';
import { state } from '../core/state.js';

const INTRO = 'Totals combine each matched app bundle with measured Library locations. Matching uses app identifiers and names; protected or unmeasured locations are excluded. Ambiguous folders are kept separate.';

function appCard(app, dirByPath) {
  const bundle = dirByPath.get(app.appPath);
  const locations = app.locations.map((d) => locationRow(d)).join('') || empty('No readable data locations matched.');
  return card({
    title: app.name,
    subtitle: `${sizeOrUnavailable(app.total)} measured · ${sizeOrUnavailable(app.appBytes)} app + ${sizeOrUnavailable(app.dataBytes)} data${app.partial ? ' · partial' : ''}`,
    bodyHtml: `
      <details>
        <summary>Show ${app.locations.length} data locations</summary>
        <p class="maphint">${esc(app.bundleId)}</p>
        ${locations}
        <p>${bundle ? infoButton('dir', bundle.id) : esc(app.appPath)}</p>
      </details>`,
  });
}

const unmatchedRow = (d) => `
  <div>
    ${locationRow(d)}
    ${d.possibly?.length ? `<p class="maphint">Possible owners: ${esc(d.possibly.join(', '))}</p>` : ''}
  </div>`;

export function appsView() {
  const data = state.insights?.apps;
  if (!data) return loading();
  const dirByPath = new Map(state.report.dirs.map((d) => [d.path, d]));
  const apps = data.apps.filter((app) => matchesText(app.name, app.bundleId, app.appPath));
  const unmatched = data.unmatched.filter((d) => matchesText(d.name, d.path));

  return `
    ${insightSearch()}
    ${notice(INTRO, { info: true })}
    ${apps.map((app) => appCard(app, dirByPath)).join('')}
    ${card({
      title: 'Unassigned Library Folders',
      subtitle: 'No clear owner was found. These are not automatically safe to remove.',
      bodyHtml: unmatched.map(unmatchedRow).join('') || empty('No large unmatched folders in the readable inventory.'),
    })}`;
}
