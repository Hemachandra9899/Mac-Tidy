import { folderRows } from '../components/folder-row.js';
import { freeSpaceMetric, metric, metricRow, trashMetric } from '../components/metrics.js';
import { actionButton, card, chartColor, coverageNote, empty, linkTo } from '../components/primitives.js';
import { esc, formatSize, formatTime, sortBySize, sumSizes } from '../core/format.js';
import { friendlyName, managedAppData, shortPath } from '../core/selectors.js';
import { state } from '../core/state.js';

const FREE_COLOR = '#e7ebdf';
const MAX_APP_CACHES = 5;
const MIN_LEGEND_BYTES = 1e6;

const STEPS = [
  ['Review the suggestion', 'Check the exact path, reason and estimated size. Reveal it in Finder if you want a closer look.'],
  ['Approve the move to Trash', 'Finish active work and quit the app. Only the item you approve is moved.'],
  ['Recover or reclaim', 'Find moved items in Activity. Empty Trash yourself when certain, then rescan to measure free space.'],
];

function diskSegments(report) {
  const roots = sortBySize(report.roots);
  const unmeasured = Math.max(0, report.disk.used - sumSizes(roots));
  const segments = [
    ...roots.map((r) => ({ name: r.path === report.home ? 'Your files & app data' : r.name, size: r.size })),
    { name: 'Other / unmeasured', size: unmeasured },
    { name: 'Available at scan', size: report.disk.free },
  ];
  const last = segments.length - 1;
  return segments.map((segment, i) => ({ ...segment, color: i === last ? FREE_COLOR : chartColor(i) }));
}

function storageCard(report) {
  const segments = diskSegments(report);
  const { total, used } = report.disk;
  const bar = segments.map((s) =>
    `<span title="${esc(s.name)}: ${formatSize(s.size)}" style="width:${(s.size / total) * 100}%;background:${s.color}"></span>`).join('');
  const legend = segments.filter((s) => s.size > MIN_LEGEND_BYTES).map((s) =>
    `<span><i class="dot" style="background:${s.color}"></i>${esc(s.name)} <b>${formatSize(s.size)}</b></span>`).join('');
  return card({
    title: 'Storage Usage at Last Scan',
    subtitle: `${formatSize(total)} shared APFS capacity · ${Math.round((used / total) * 100)}% allocated or unavailable`,
    asideHtml: actionButton('Explore folders ↗', 'go', { arg: 'explorer', style: 'linkbutton' }),
    bodyHtml: `
      <div class="diskbar">${bar}</div>
      <div class="legend">${legend}</div>
      <p class="maphint">Folder sizes are from the last scan. APFS shared blocks and protected folders prevent exact reconciliation. Suggested space is an estimate, not guaranteed savings.</p>`,
  });
}

const hero = (largest) => !largest ? '' : `
  <div class="hero-cleanup">
    <div>
      <div class="eyebrow">Largest cleanup opportunity</div>
      <h2>${formatSize(largest.size)} in ${esc(friendlyName(largest))}</h2>
      <p>Caches can be recreated. Quit the owning app and stop any builds before reviewing removal.</p>
      <code>${esc(shortPath(largest.path))}</code>
    </div>
    <div class="actions stacked">
      ${actionButton('Review Removal…', 'review-trash', { arg: `dir:${largest.id}`, style: 'button primary' })}
    </div>
  </div>`;

const stepsCard = () => card({
  title: 'Review Before Removing',
  subtitle: 'One location. One clear decision.',
  bodyHtml: STEPS.map(([title, text], i) =>
    `<div class="step"><span class="stepnum">${i + 1}</span><div><b>${title}</b><p>${text}</p></div></div>`).join(''),
});

export function overviewView() {
  const { report, cleanup } = state;
  const cards = cleanup.cards;
  const appCaches = cards.filter((d) => d.path.includes('/Library/Caches/')).slice(0, MAX_APP_CACHES);

  return `
    ${metricRow(
      freeSpaceMetric('Filesystem space at last refresh'),
      metric('Reviewable caches', sumSizes(cards), `${cards.length} independent locations to review`, { highlight: true }),
      trashMetric('Estimated size of items still in Trash'),
      metric('Measured files', sumSizes(report.roots), `${report.filesScanned.toLocaleString()} files · ${formatTime(report.finished)} · partial`),
    )}
    ${hero(cards[0])}
    ${storageCard(report)}
    <div class="split">
      ${card({
        title: 'App Caches',
        subtitle: 'Individual app folders, not the entire Library.',
        asideHtml: linkTo('Review all →', 'approvals'),
        bodyHtml: folderRows(appCaches, empty('No large app caches found.')),
      })}
      ${stepsCard()}
    </div>
    ${card({
      title: 'Managed App Data',
      subtitle: 'These can contain valuable media, virtual machines and persistent data.',
      bodyHtml: folderRows(managedAppData(), empty('Use Browse Storage to review other large folders.')),
    })}
    ${card({title:'Understand What to Review',subtitle:'Explore measured evidence before choosing cleanup.',bodyHtml:`<div class="insight-links">${linkTo('Apps →','apps')}${linkTo('Developer storage →','developer')}${linkTo('Older files →','older')}${linkTo('Exact duplicates →','duplicates')}${linkTo('Storage trends →','trends')}${linkTo('Why space differs →','space')}</div>`})}
    ${coverageNote()}`;
}
