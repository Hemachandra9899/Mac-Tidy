import { esc,formatSize,formatDateTime } from '../core/format.js';
import { state } from '../core/state.js';
import { shortPath } from '../core/selectors.js';
import { actionButton as button,card,notice,empty,linkTo } from '../components/primitives.js';
import { metric,metricRow } from '../components/metrics.js';
const num=n=>Number(n||0).toLocaleString();
const measured=(label,n,note)=>n===undefined||n===null?`<div class="metric"><div class="metric-label">${esc(label)}</div><strong class="unavailable-value">Unavailable</strong><small>${esc(note)}</small></div>`:metric(label,n,note);
const size=n=>n===null||n===undefined?'Unavailable':formatSize(n);
const date=t=>formatDateTime(t);
const info=(type,id)=>button('Information…','details',{arg:`${type}:${id}`,style:'linkbutton'});
const review=(type,row)=>row.trashPolicy?.allowed?button('Review Removal…','review-trash',{arg:`${type}:${row.id??row.index}`,style:'button'}):'<span class="pill">Manage in owning app</span>';
const loading=()=>'<div class="loading-card"><span class="spinner"></span>Preparing storage insights…</div>';
function lookup(path){return state.report.dirs.find(d=>d.path===path);}
function search(){return `<div class="toolbar"><input id="search" type="search" aria-label="Search insights" placeholder="Search names and locations" value="${esc(state.query)}"></div>`;}
function matches(...values){const q=state.query.toLowerCase();return !q||values.some(v=>String(v||'').toLowerCase().includes(q));}
function location(d,type='dir'){return `<div class="insight-location"><div class="rowname"><b>${esc(d.name||d.label||d.path.split('/').pop())}</b><small title="${esc(d.path)}">${esc(shortPath(d.path))}${d.partial?' · partial':''}</small></div><b class="insight-size">${size(d.size)}</b>${info(type,d.id??d.index)}</div>`;}

export function appsView(){
 const data=state.insights?.apps;if(!data)return loading();
 const apps=data.apps.filter(a=>matches(a.name,a.bundleId,a.appPath));
 return search()+notice('Totals combine each matched app bundle with measured Library locations. Matching uses app identifiers and names; protected or unmeasured locations are excluded. Ambiguous folders are kept separate.',{info:true})+
 apps.map(app=>card({title:app.name,subtitle:`${size(app.total)} measured · ${size(app.appBytes)} app + ${size(app.dataBytes)} data${app.partial?' · partial':''}`,bodyHtml:`<details><summary>Show ${app.locations.length} data locations</summary><p class="maphint">${esc(app.bundleId)}</p>${app.locations.map(d=>location(d)).join('')||empty('No readable data locations matched.')}<p>${lookup(app.appPath)?info('dir',lookup(app.appPath).id):esc(app.appPath)}</p></details>`})).join('')+
 card({title:'Unassigned Library Folders',subtitle:'No clear owner was found. These are not automatically safe to remove.',bodyHtml:data.unmatched.filter(d=>matches(d.name,d.path)).map(d=>`<div>${location(d)}${d.possibly?.length?`<p class="maphint">Possible owners: ${esc(d.possibly.join(', '))}</p>`:''}</div>`).join('')||empty('No large unmatched folders in the readable inventory.')});
}
export function developerView(){
 const data=state.insights?.developer;if(!data)return loading();
 const projects=data.projects.filter(p=>matches(p.project,p.path)&&(!state.staleOnly||p.stale));
 const safeCommands=['docker system df','brew cleanup -n','rustup toolchain list'];
 return metricRow(metric('Project dependencies',data.projectBytes,`${num(data.projects.length)} top-level node_modules folders`),metric('Older project candidates',data.staleBytes,`No observed changes for ${data.staleDays}+ days; review required`))+
 notice('Age is a clue, not proof of disuse. Project age uses the latest observed modification across the project. Reinstalling dependencies may require network access and may lose local dependency edits. Tool and project categories may overlap; do not add these totals as promised savings.',{info:true})+search()+
 card({title:'Tool Storage',subtitle:'What each location holds and how to review it.',bodyHtml:data.tools.filter(t=>matches(t.name,t.path)).map(t=>`<section class="tool-row"><div class="card-head"><div><h3>${esc(t.name)}</h3><p>${esc(t.advice)}</p></div><b>${size(t.size)}</b></div><code class="insight-path">${esc(shortPath(t.path))}</code>${safeCommands.includes(t.command)?`<p class="maphint">Read-only inspection command</p><code class="insight-path">${esc(t.command)}</code>`:''}<div class="actions">${info('dir',t.id)}${review('dir',t)}</div></section>`).join('')||empty('No supported tool locations found in this scan.')})+
 card({title:'Project Dependencies',asideHtml:`<label class="inline-check"><input type="checkbox" id="stale-only" ${state.staleOnly?'checked':''}>Older projects only</label>`,bodyHtml:projects.slice(0,150).map(p=>`<section class="tool-row"><div class="card-head"><div><h3>${esc(p.project)}</h3><p>${p.ageDays} days since latest observed change${p.stale?' · possible cleanup candidate':''}</p></div><b>${size(p.size)}</b></div><code class="insight-path">${esc(shortPath(p.path))}</code><div class="actions">${info('dir',p.id)}${review('dir',p)}</div></section>`).join('')||empty('No projects match this filter.')});
}
export function olderView(){
 const data=state.insights?.older;if(!data)return loading();
 const rows=data.files.filter(f=>f.ageDays>=state.oldDays&&matches(f.path,f.name));
 return notice('These files have not been modified recently. A file can still be useful or frequently opened without being modified. Last-opened time is not inferred, and no file is selected for removal automatically.',{info:true})+
 `<div class="toolbar"><label>Unchanged for <select id="old-days">${[90,180,365,730].map(n=>`<option value="${n}" ${n===state.oldDays?'selected':''}>${n} days</option>`).join('')}</select></label><input type="search" id="search" aria-label="Search insights" placeholder="Search files and paths" value="${esc(state.query)}"></div>`+
 card({title:`${num(rows.length)} older files`,subtitle:`${num(data.indexedFiles)} indexed personal files considered. Largest matches shown first.`,bodyHtml:rows.slice(0,200).map(f=>`<section class="old-file-row"><div class="rowname"><b>${esc(f.name)}</b><small title="${esc(f.path)}">${esc(shortPath(f.path))}</small><small>Modified ${date(f.mtime)} · ${f.ageDays} days ago</small></div><div><b>${size(f.size)}</b><div class="actions">${info(f.type,f.index)}${review(f.type,f)}</div></div></section>`).join('')||empty('No indexed files match this age and search.')})+`<p class="maphint">${esc(data.scope)} A fresh scan indexes up to ${num(state.report.reviewFilesLimit||10000)} personal files of at least 1 MB.</p>`;
}
function graph(points){
 if(points.length<2)return empty('A second completed scan will start the chart. No historical data is fabricated.');
 const w=600,h=190,pad=32,max=Math.max(...points.map(p=>p.total)),x=i=>pad+i*(w-2*pad)/(points.length-1),y=n=>h-pad-n/max*(h-2*pad);
 return `<svg class="trend-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Allocated storage over ${points.length} completed scans"><line x1="${pad}" y1="${h-pad}" x2="${w-pad}" y2="${h-pad}" class="chart-axis"/><text x="0" y="${pad}">${esc(size(max))}</text><text x="3" y="${h-pad}">0</text><polyline points="${points.map((p,i)=>`${x(i)},${y(p.used)}`).join(' ')}" fill="none" class="chart-line"/>${points.map((p,i)=>`<circle cx="${x(i)}" cy="${y(p.used)}" r="3" class="chart-dot"><title>${esc(p.finished)}: ${size(p.used)} allocated</title></circle>`).join('')}</svg><div class="chart-dates"><span>${esc(new Date(points[0].finished).toLocaleString())}</span><span>${esc(new Date(points.at(-1).finished).toLocaleString())}</span></div>`;
}
export function trendsView(){
 const data=state.trends;if(!data)return loading();const points=data.points,last=points.at(-1),previous=points.at(-2),delta=previous&&last?last.free-previous.free:null;
 return (data.saveWarning?notice(esc(data.saveWarning)):'')+(last?metricRow(metric('Available at latest scan',last.free,new Date(last.finished).toLocaleString()),measured(delta===null?'Previous scan needed':delta>=0?'Available-space increase':'Available-space decrease',delta===null?null:Math.abs(delta),'Filesystem change; not proof that cleanup caused it')):'')+
 card({title:'Storage Over Time',subtitle:`${points.length} real scan snapshots · up to 60 retained`,bodyHtml:graph(points)})+
 card({title:'What Changed?',subtitle:data.coverageNote,bodyHtml:data.changes.map(c=>`<div class="insight-location"><div class="rowname"><b title="${esc(c.path)}">${esc(shortPath(c.path))}</b><small>${size(c.before)} → ${size(c.after)}</small></div><strong class="${c.delta<0?'reduced':'increased'}">${c.delta>0?'+':'−'}${size(Math.abs(c.delta))}</strong></div>`).join('')||empty(points.length<2?'Complete another scan to compare.':'No comparable folder changed by at least 200 MB. Missing or partially read folders are not treated as reclaimed space.')})+
 notice('The history stores 60 capacity points and only the latest two folder baselines to keep its own footprint small. Free-space changes include background app activity and APFS behavior.',{info:true});
}
export function spaceView(){
 const data=state.space||{};const capacity=data.capacity;
 return (data.status==='loading'?notice('Refreshing macOS space estimates and local snapshot names…',{info:true}):'')+
 metricRow(metric('Filesystem free',capacity?.free??state.cleanup.diskFree,'Space reported available now'),measured('Available for important use',capacity?.freeIncludingPurgeable,capacity?'Native macOS estimate; includes reclaimable capacity':'Native estimate unavailable'),measured('Potentially reclaimable',data.purgeable,data.purgeable===null||data.purgeable===undefined?'Estimate unavailable':'Difference between macOS capacity estimates'))+
 card({title:'Why the Numbers Differ',bodyHtml:`<div class="step"><span class="stepnum">1</span><div><b>Trash still occupies storage</b><p>${data.trashBytes===null||data.trashBytes===undefined?'Trash size could not be read.':`${size(data.trashBytes)} measured in this user’s Trash.`} Moving files to Trash is reversible; space is generally reclaimed only after you empty it yourself.</p></div></div><div class="step"><span class="stepnum">2</span><div><b>macOS can reclaim some capacity</b><p>“Available for important use” is an operating-system estimate, not a list of disposable files. Snapshots, caches and storage reservations affect the difference.</p></div></div><div class="step"><span class="stepnum">3</span><div><b>Copies can share APFS blocks</b><p>Equal file content or large logical file sizes do not guarantee that deleting one copy will free the displayed number of bytes.</p></div></div>${data.checkedAt?`<p class="maphint">Checked ${date(data.checkedAt)}. Estimates refresh at most once per minute.</p>`:''}`})+
 card({title:'Local Time Machine Snapshots',subtitle:data.snapshots===null||!data.snapshots?'Snapshot names unavailable':`${data.snapshots.length} names reported; sizes are not measured`,bodyHtml:data.snapshots?.length?`<ul class="snapshot-list">${data.snapshots.map(n=>`<li><code>${esc(n)}</code></li>`).join('')}</ul>`:empty('No local Time Machine snapshot names were returned, or access is unavailable.')})+
 `<p class="maphint">Mac Tidy does not delete snapshots or empty Trash. <a href="https://support.apple.com/en-us/102154" target="_blank" rel="noreferrer">Apple’s snapshot explanation ↗</a> · <a href="https://developer.apple.com/documentation/foundation/urlresourcevalues/volumeavailablecapacityforimportantusage" target="_blank" rel="noreferrer">Native capacity API ↗</a></p>`;
}
export function duplicatesView(){
 const result=state.duplicates||{status:'idle',groups:[]};const running=result.status==='running',stale=result.revision&&result.revision!==state.report.finished;
 const controls=`<div class="toolbar"><label>Compare <select id="duplicate-mode" ${running?'disabled':''}><option value="files" ${state.duplicateMode==='files'?'selected':''}>Files</option><option value="folders" ${state.duplicateMode==='folders'?'selected':''}>Folders</option></select></label><label>Read budget <select id="duplicate-budget" ${running?'disabled':''}>${[2,8,32].map(n=>`<option value="${n*1e9}" ${state.duplicateBudget===n*1e9?'selected':''}>${n} GB</option>`).join('')}</select></label>${button(running?'Searching…':'Find Exact Duplicates','find-duplicates',{style:'button primary',disabled:running})}${running?button('Cancel','cancel-duplicates'):''}</div>`;
 let content='';
 if(running)content=notice(`<span class="spinner"></span> ${size(result.bytesHashed||0)} read · search running locally. You can cancel without changing files.`,{info:true});
 else if(stale)content=notice('The storage report changed. Start a new duplicate search before reviewing removal.');
 else if(result.status==='error')content=notice(esc(result.message));
 else if(result.status==='cancelled')content=empty('Search cancelled. No files were moved.');
 else if(result.status==='complete'){
  content=`<div class="queue-summary"><div><b>${result.groups.length} verified groups</b><span>${size(result.wasted||0)} of repeated logical content; actual disk savings may be lower</span></div></div>`;
  content+=result.groups.map(g=>{
   if(result.mode==='folders')return card({title:`Matching folders · ${size(g.size)} content each`,subtitle:'Relative names, empty directories and full file SHA-256 hashes match. Whole-folder removal is not offered here.',bodyHtml:g.folders.map(d=>location(d)).join('')});
   const requested=state.duplicateKeepers[g.id]??g.keeper;const keeper=g.files.some(f=>f.index===requested)?requested:g.keeper;
   return card({title:`${g.files.length} matching copies · ${size(g.size)} each`,subtitle:'Choose the copy to keep. Each other copy still requires its own removal approval.',bodyHtml:g.files.map(f=>`<div class="duplicate-file"><label><input type="radio" name="keeper-${g.id}" data-keeper-group="${g.id}" value="${f.index}" ${f.index===keeper?'checked':''}><span><b>${f.index===keeper?'Keep this copy':'Other copy'}</b><code>${esc(shortPath(f.path))}</code></span></label><div class="actions">${info(f.type||'file',f.index)}${f.index!==keeper&&f.trashPolicy?.allowed?button('Review Duplicate…','review-duplicate',{arg:JSON.stringify({group:g.id,id:f.index,keeper}),style:'button'}):''}</div></div>`).join('')});
  }).join('')||empty('No verified duplicates within the chosen scope and budget.');
  content+=`<p class="maphint">${esc(result.scope||'')} ${result.skippedBudget||0} candidates skipped for the read budget; ${result.skippedChanged||0} excluded, unreadable or changed candidates. Results can change as apps modify files.</p>`;
 }
 return notice('This search reads local file contents only when started. It excludes symlinks, hard links counted as one file, cloud placeholders, app/Photos packages, hidden files and dependency trees. No file is removed automatically.',{info:true})+controls+content+(result.status==='idle'?card({bodyHtml:empty('Start a search to verify exact matches. Similar-looking photos are not treated as identical files. Folder comparisons inspect only complete, size-matched candidates.')}):'');
}
