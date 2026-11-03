// View registry: page titles and the function that renders each view's content.

import { activityView } from './activity.js';
import { explorerView } from './explorer.js';
import { itemListView } from './item-list.js';
import { overviewView } from './overview.js';
import { reviewCleanupView } from './review-cleanup.js';
import { scanDetailsView } from './scan-details.js';

const view = (title, subtitle, render, crumb = title) => ({ title, subtitle, crumb, render });

export const VIEWS = {
  overview: view('Storage', 'Understand what’s on your Mac. Choose what to remove.', overviewView, 'Overview'),
  approvals: view('Review Cleanup', 'Review temporary files and choose what to move to Trash.', reviewCleanupView),
  activity: view('Activity & Recovery', 'Review completed removals and find items in Trash.', activityView),
  explorer: view('Browse Storage', 'Open folders to see what’s using space on your Mac.', explorerView),
  cleanup: view('All Candidates', 'Inspect cache locations, downloads and other items that need review.', () => itemListView('cleanup')),
  files: view('Large Files', 'Find large files and review their exact locations.', () => itemListView('files')),
  coverage: view('Scan Details', 'Measured locations, access limitations and storage accounting.', scanDetailsView),
};
