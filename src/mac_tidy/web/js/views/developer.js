import { infoButton, insightSearch, loading, reviewButton, toolRow } from '../components/insight-rows.js';
import { measuredMetric, metric, metricRow } from '../components/metrics.js';
import { card, empty, notice } from '../components/primitives.js';
import { esc } from '../core/format.js';
import { matchesText } from '../core/selectors.js';
import { state } from '../core/state.js';

const MAX_PROJECTS = 150;
// Only commands that inspect and never change anything are shown.
const READ_ONLY_COMMANDS = ['docker system df', 'brew cleanup -n', 'rustup toolchain list'];
const INTRO = 'Age is a clue, not proof of disuse. Project age uses the latest observed modification across the project. Reinstalling dependencies may require network access and may lose local dependency edits. Tool and project categories may overlap; do not add these totals as promised savings.';

const actions = (row) => infoButton('dir', row.id) + reviewButton('dir', row);

function toolEntry(tool) {
  const inspection = READ_ONLY_COMMANDS.includes(tool.command)
    ? `<p class="maphint">Read-only inspection command</p><code class="insight-path">${esc(tool.command)}</code>`
    : '';
  return toolRow({
    title: tool.name,
    subtitle: tool.advice,
    size: tool.size,
    path: tool.path,
    extraHtml: inspection,
    actionsHtml: actions(tool),
  });
}

const projectEntry = (project) => toolRow({
  title: project.project,
  subtitle: `${project.ageDays} days since latest observed change${project.stale ? ' · possible cleanup candidate' : ''}`,
  size: project.size,
  path: project.path,
  actionsHtml: actions(project),
});

export function developerView() {
  const data = state.insights?.developer;
  if (!data) return loading();
  const tools = data.tools.filter((tool) => matchesText(tool.name, tool.path));
  const projects = data.projects.filter((p) => matchesText(p.project, p.path) && (!state.staleOnly || p.stale));
  const staleOnlyToggle = `
    <label class="inline-check">
      <input type="checkbox" id="stale-only" ${state.staleOnly ? 'checked' : ''}>Older projects only
    </label>`;

  return `
    ${metricRow(
      metric('Project dependencies', data.projectBytes, `${data.projects.length.toLocaleString()} top-level node_modules folders`),
      measuredMetric('Older project candidates', data.staleBytes, `No observed changes for ${data.staleDays}+ days; review required`),
    )}
    ${notice(INTRO, { info: true })}
    ${insightSearch()}
    ${card({
      title: 'Tool Storage',
      subtitle: 'What each location holds and how to review it.',
      bodyHtml: tools.map(toolEntry).join('') || empty('No supported tool locations found in this scan.'),
    })}
    ${card({
      title: 'Project Dependencies',
      asideHtml: staleOnlyToggle,
      bodyHtml: projects.slice(0, MAX_PROJECTS).map(projectEntry).join('') || empty('No projects match this filter.'),
    })}`;
}
