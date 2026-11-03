import { folderRow } from '../components/folder-row.js';
import { metric, metricRow } from '../components/metrics.js';
import { card, notice } from '../components/primitives.js';
import { esc, sumSizes } from '../core/format.js';
import { shortPath } from '../core/selectors.js';
import { state } from '../core/state.js';

const APPLE_STORAGE_GUIDE = 'https://support.apple.com/guide/mac-help/change-storage-settings-mchl3d437fbc/mac';

const errorRow = (e) => `
  <div class="step"><div class="wrap-anywhere">
    <b>${esc(shortPath(e.path))}</b>
    <p>${esc(e.reason)}</p>
  </div></div>`;

const coverageCard = (report) => card({
  title: 'What the scan covers',
  bodyHtml: `
    <p class="maphint">${report.filesScanned.toLocaleString()} files and ${report.dirsScanned.toLocaleString()} directories scanned in ${report.elapsed} seconds. Roots are listed below. External drives and symlinks were skipped; hard-linked files were counted once. Package bundles were measured. Top-file indexing is capped at 1,500 entries; folders of at least 1 MB remain browsable, plus their ancestors and indexed-file parents.</p>
    ${report.roots.map((d) => folderRow(d, Math.max(...report.roots.map((r) => r.size)))).join('')}
    <p class="maphint">${esc(report.snapshots)} APFS clones may share blocks, so deleting an item may reclaim less than its displayed allocated size. File totals exclude directory metadata. The disk metric uses filesystem capacity minus free blocks, which includes shared APFS allocations and differs from df’s data-volume-only used value. This is not Apple’s System Data category.</p>
    <p class="maphint">For Apple’s category breakdown, open System Settings → General → Storage. If you choose to grant your terminal Full Disk Access, restart it and Mac Tidy, then rescan. This is optional.</p>
    <a class="linkbutton" href="${APPLE_STORAGE_GUIDE}" target="_blank" rel="noreferrer">Apple’s storage settings guide ↗</a>`,
});

export function scanDetailsView() {
  const { report } = state;
  const measured = sumSizes(report.roots);

  return `
    ${notice('This scan is partial. macOS privacy controls protect locations including Mail, Photos and other app data. No permissions were changed. Unreadable locations are not empty folders.')}
    ${metricRow(
      metric('Measured file data', measured, 'Allocated bytes, excluding symlinks'),
      metric('Unreconciled difference', Math.max(0, report.disk.used - measured), 'Not a System Data measurement'),
    )}
    ${coverageCard(report)}
    ${card({
      title: 'Unreadable locations',
      subtitle: `${report.errorsCount} errors; first ${report.errors.length} shown.`,
      bodyHtml: report.errors.map(errorRow).join('') || '<p>No unreadable locations reported.</p>',
    })}`;
}
