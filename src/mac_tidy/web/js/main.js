// App entry point.

import { bindEvents } from './app/events.js';
import { poll } from './app/sync.js';
import { state } from './core/state.js';
import { VIEWS } from './views/index.js';

const initialView = location.hash.slice(1);
if (VIEWS[initialView]) state.view = initialView;

bindEvents();
poll();
