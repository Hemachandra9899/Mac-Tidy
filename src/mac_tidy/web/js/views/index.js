// View registry: page titles and the function that renders each view's content.

import { activityView } from './activity.js';
import { appsView } from './apps.js';
import { developerView } from './developer.js';
import { duplicatesView } from './duplicates.js';
import { explorerView } from './explorer.js';
import { spaceView } from './free-space.js';
import { itemListView } from './item-list.js';
import { olderView } from './older-files.js';
import { overviewView } from './overview.js';
import { reviewCleanupView } from './review-cleanup.js';
import { scanDetailsView } from './scan-details.js';
import { trendsView } from './trends.js';

const view = (title, subtitle, render, crumb = title) => ({ title, subtitle, crumb, render });

export const VIEWS = {
  overview: view('Storage', 'Understand what’s on your Mac. Choose what to remove.', overviewView, 'Overview'),
  approvals: view('Review Cleanup', 'Review temporary files and choose what to move to Trash.', reviewCleanupView),
  explorer: view('Browse Storage', 'Open folders to see what’s using space on your Mac.', explorerView),
  files: view('Large Files', 'Find large files and review their exact locations.', () => itemListView('files')),
  cleanup: view('All Candidates', 'Inspect cache locations, downloads and other items that need review.', () => itemListView('cleanup')),
  apps: view('Apps', 'One measured total per app, across its bundle and readable data locations.', appsView),
  developer: view('Developer Storage', 'Understand tool caches, build output and older project dependencies.', developerView),
  older: view('Older Files', 'Review large personal files by modification age—not assumed disuse.', olderView),
  duplicates: view('Exact Duplicates', 'Compare local content with a read budget. Keep a copy before reviewing removal.', duplicatesView),
  trends: view('Storage Trends', 'Real scan history and comparable folder changes.', trendsView),
  space: view('Free Space Explained', 'Why filesystem free space, macOS estimates and Trash differ.', spaceView),
  activity: view('Activity & Recovery', 'Review completed removals and find items in Trash.', activityView),
  coverage: view('Scan Details', 'Measured locations, access limitations and storage accounting.', scanDetailsView),
};
