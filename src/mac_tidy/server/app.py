"""Application state and use cases behind the HTTP API."""

import datetime
import os
import secrets
import shutil
import threading
import time
from pathlib import Path

from .. import __version__
from ..cleanup import ActivityLog, TrashManager, native
from ..common.jsonfile import read_json, write_json_atomic
from ..config import DATA_DIR, HOME, PACKAGE_DIR
from ..insights.apps import app_breakdown, installed_apps
from ..insights.developer import developer_summary
from ..insights.duplicates import DuplicateFinder, DEFAULT_BUDGET, MAX_BUDGET
from ..insights.old_files import older_files, review_inventory
from ..cleanup.fingerprint import fingerprint
from ..insights.space import space_summary
from ..insights.trends import TrendLog
from ..scan import ROOTS, data_volume, prepare_report, recommendations, scan_tree

SCANNING_STATE = {
    "status": "scanning",
    "current": "Preparing scan…",
    "filesScanned": 0,
    "dirsScanned": 0,
    "errorsCount": 0,
    "elapsed": 0,
}


class App:
    """Scan state, the current report and Trash actions.

    ``lock`` guards ``state`` and ``report`` and is held only briefly.
    ``action_lock`` serialises starting a scan and running a Trash move, so a
    scan can never replace the report while an approved move is running.
    """

    def __init__(self, data_dir=DATA_DIR, mover=native.move_to_trash, revealer=native.reveal, roots=ROOTS,
                 home=HOME, volume_space=native.volume_space):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.report_file = self.data_dir / "report.json"
        self.roots = roots
        self.home = home
        self.reveal = revealer
        self.volume_space = volume_space
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.action_lock = threading.Lock()
        self.state = {"status": "starting"}
        self.report = None
        self.activity = ActivityLog(self.data_dir / "activity.json")
        self.trash = TrashManager(self.activity, mover, home=home)
        self.trends = TrendLog(self.data_dir / "trends.json")
        self.duplicates = DuplicateFinder()
        self._space_cache = (0, None)
        self._space_running = False
        self._space_lock = threading.Lock()
        self._duplicate_guards = {}
        self._report_insights = (None, None)  # (revision, insights derived from that report)

    # Report lifecycle

    def _set_report(self, report):
        with self.lock:
            self.report = report
            self.state = {"status": "complete"}
        self.trends.record(report)
        self.duplicates.reset()

    def _set_state(self, state):
        with self.lock:
            self.state = state

    def load_saved_report(self):
        try:
            self._set_report(prepare_report(read_json(self.report_file)))
        except (OSError, ValueError, KeyError):
            return False
        return True

    def start_scan(self):
        with self.action_lock, self.lock:
            if self.state["status"] == "scanning":
                return False
            self.state = dict(SCANNING_STATE)
            self.duplicates.cancel()
        threading.Thread(target=self._scan, daemon=True).start()
        return True

    def _scan(self):
        try:
            report = prepare_report(scan_tree(self.roots, self._set_state))
            write_json_atomic(self.report_file, report)
            self._set_report(report)
        except Exception as ex:  # surface any failure to the UI instead of a stuck spinner
            self._set_state({"status": "error", "message": str(ex)})

    def _require_report(self):
        """The current report's revision. Caller holds ``lock``."""
        if self.state["status"] == "scanning" or not self.report:
            raise ValueError("Wait for the scan to finish.")
        return self.report["finished"]

    def was_moved(self, path):
        """True if ``path`` or an ancestor was moved to Trash since the last scan."""
        since = datetime.datetime.fromisoformat(self.report["finished"]).timestamp() if self.report else 0
        return self.activity.moved_since(path, since)

    # Read endpoints

    def status(self):
        with self.lock:
            return {
                **self.state,
                "version": __version__,
                "hasReport": self.report is not None,
                "reportFinished": self.report["finished"] if self.report else None,
                "activityCount": len(self.activity),
                "projectPath": str(PACKAGE_DIR),
                "pid": os.getpid(),
            }

    def get_report(self):
        with self.lock:
            return self.report or {"status": "scanning"}

    def cleanup(self):
        history = self.activity.with_status()
        with self.lock:
            cards = recommendations(self.report, self.was_moved)
        return {
            "cards": cards,
            "history": list(reversed(history)),
            "diskFree": shutil.disk_usage(data_volume()).free,
            "bytesInTrash": sum(h["size"] for h in history if h["status"] == "in_trash"),
            "unverifiedTrashCount": sum(h["status"] == "unknown" for h in history),
        }

    # Insights

    def _derived_insights(self, report):
        """Developer and per-app summaries, computed once per report."""
        revision, cached = self._report_insights
        if revision != report["finished"]:
            cached = {
                "developer": developer_summary(report, time.time()),
                "apps": app_breakdown(report, installed_apps()),
                "older": older_files(report, time.time()),
            }
            self._report_insights = (report["finished"], cached)
        return cached

    def insights(self):
        with self.lock:
            report = self.report
            derived = self._derived_insights(report) if report else {"developer": None, "apps": None, "older": None}
        return derived

    def space(self):
        with self._space_lock:
            stamp,data=self._space_cache
            if (data is None or time.time()-stamp>60) and not self._space_running:
                self._space_running=True
                threading.Thread(target=self._refresh_space,daemon=True).start()
            return {'status':'loading' if self._space_running else 'complete',**(data or {})}

    def _refresh_space(self):
        try:data={**space_summary(self.volume_space,self.home),'checkedAt':time.time()}
        except Exception as ex:data={'capacity':None,'snapshots':None,'trashBytes':None,'message':str(ex),'checkedAt':time.time()}
        with self._space_lock:self._space_cache=(time.time(),data);self._space_running=False

    def trends_summary(self):
        return self.trends.summary()

    def duplicates_status(self):
        return self.duplicates.status()

    def find_duplicates(self, body):
        mode=body.get('mode','files')
        if mode not in ('files','folders'):raise ValueError('Choose files or folders.')
        budget=body.get('budgetBytes',DEFAULT_BUDGET)
        if type(budget) is not int or not 1_000_000 <= budget <= MAX_BUDGET:raise ValueError('Read budget must be between 1 MB and 32 GB.')
        with self.lock:
            revision=self._require_report();report=self.report
            rows,collection=review_inventory(report)
            files=[{**f,'index':i,'type':collection} for i,f in enumerate(rows)]
        return {'started':self.duplicates.start(files,revision,home=self.home,mode=mode,report=report,budget=budget)}

    def cancel_duplicates(self,_body):
        return self.duplicates.cancel()

    def preview_duplicate(self,body):
        with self.action_lock,self.lock:
            revision=self._require_report();result=self.duplicates.status()
            if result.get('status')!='complete' or result.get('mode')!='files' or result.get('revision')!=revision:raise ValueError('Run a current file duplicate search first.')
            group=next((g for g in result.get('groups',[]) if g['id']==body.get('group')),None)
            if not group:raise ValueError('Duplicate group no longer available.')
            target=next((f for f in group['files'] if f['index']==body.get('id')),None)
            keeper=next((f for f in group['files'] if f['index']==body.get('keeper')),None)
            if not target or not keeper or target['path']==keeper['path']:raise ValueError('Choose a different copy to keep.')
            try:
                if fingerprint(target['path'])!=target['fingerprint'] or fingerprint(keeper['path'])!=keeper['fingerprint']:raise ValueError('A copy changed. Run duplicate search again.')
            except OSError:raise ValueError('A copy is missing. Run duplicate search again.') from None
            row=self._resolve_row({'type':target.get('type','file'),'id':target['index'],'path':target['path']})
            plan=self.trash.preview(row,'file',revision)
            self._duplicate_guards[plan['approval']]={'keeper':keeper['path'],'fingerprint':keeper['fingerprint']}
            return {**plan,'keeper':keeper['path']}

    # Actions

    def _resolve_row(self, body):
        """Map a browser selection back to a scanned row and confirm it still matches."""
        if not self.report:
            raise ValueError("Wait for the scan to finish.")
        if body.get("type") not in ("dir", "file", "review-file"):
            raise ValueError("Invalid item type")
        rows = self.report["dirs"] if body["type"] == "dir" else self.report.get("reviewFiles",[]) if body["type"]=="review-file" else self.report["files"]
        index = body.get("id")
        if type(index) is not int or not 0 <= index < len(rows):
            raise ValueError("Invalid scanned item")
        row = rows[index]
        if body.get("path") != row["path"]:
            raise ValueError("The scan changed. Select the item again.")
        if not os.path.lexists(row["path"]):
            raise ValueError("Item no longer exists. Rescan to refresh.")
        return row

    def rescan(self, _body):
        return {"started": self.start_scan()}

    def reveal_item(self, body):
        with self.lock:
            row = self._resolve_row(body)
        self.reveal(row["path"])
        return {"ok": True}

    def preview_trash(self, body):
        with self.action_lock, self.lock:
            revision = self._require_report()
            row = self._resolve_row(body)
            if self.was_moved(row["path"]):
                raise ValueError("This location was already moved. Rescan before reviewing a recreated cache.")
            return self.trash.preview(row, "dir" if body["type"]=="dir" else "file", revision)

    def approve_trash(self, body):
        if body.get("confirmed") is not True:
            raise ValueError("Confirm this exact item before moving it to Trash.")
        # Keep action_lock for the whole move so no scan starts meanwhile, but
        # release ``lock`` so status polling stays responsive.
        with self.action_lock:
            with self.lock:
                revision = self._require_report()
            key=body.get("approval", "")
            guard=self._duplicate_guards.get(key)
            if guard:
                try:
                    if fingerprint(guard['keeper'])!=guard['fingerprint']:raise ValueError('The copy to keep changed. Run duplicate search again.')
                except OSError:raise ValueError('The copy to keep is missing. Nothing was moved.') from None
            item = self.trash.execute(key, revision)
            self._duplicate_guards.pop(key,None)
            self.duplicates.mark_moved(item["path"])
        return {"ok": True, "item": item}

    def reveal_activity(self, body):
        entry = self.activity.find(body.get("id"))
        if not entry:
            raise ValueError("Activity item not found")
        self.reveal(entry["trashPath"])
        return {"ok": True}

    def wait_for_actions(self):
        """Block until an in-flight Trash move has been recorded."""
        with self.action_lock:
            pass
