"""Bounded scan history: chart points plus only two full folder baselines."""
import threading
from ..common.jsonfile import read_json,write_json_atomic
MAX_POINTS=60
MIN_CHANGE_BYTES=200_000_000
MAX_CHANGES=15
EXPLAINED_SHARE=.8
def snapshot(report):
 return {'finished':report['finished'],**{k:report['disk'][k] for k in ['used','free','total']},'dirs':{d['path']:d['size'] for d in report['dirs']},'partial':[d['path'] for d in report['dirs'] if d.get('partial')],'scope':sorted(r['path'] for r in report.get('roots',[]))}
def _changes(before,after):
 if before.get('scope')!=after.get('scope'):return []
 partial=set(before.get('partial',[]))|set(after.get('partial',[]))
 changed={p:after['dirs'][p]-before['dirs'][p] for p in before['dirs'].keys()&after['dirs'].keys() if p not in partial and abs(after['dirs'][p]-before['dirs'][p])>=MIN_CHANGE_BYTES}
 def explained(path,delta):return any(other.startswith(path+'/') and abs(d)>=EXPLAINED_SHARE*abs(delta) and (d>0)==(delta>0) for other,d in changed.items())
 result=[{'path':p,'before':before['dirs'][p],'after':after['dirs'][p],'delta':d} for p,d in changed.items() if not explained(p,d)]
 return sorted(result,key=lambda c:abs(c['delta']),reverse=True)[:MAX_CHANGES]
class TrendLog:
 def __init__(self,path):
  self.path=path;self._lock=threading.Lock();self.save_warning=None
  try:self._points=read_json(path)
  except (OSError,ValueError):self._points=[]
 def record(self,report):
  with self._lock:
   if any(p['finished']==report['finished'] for p in self._points):return False
   self._points.append(snapshot(report));self._points.sort(key=lambda p:p['finished']);self._points=self._points[-MAX_POINTS:]
   for point in self._points[:-2]:
    for key in ['dirs','partial','scope']:point.pop(key,None)
   try:write_json_atomic(self.path,self._points);self.save_warning=None
   except OSError:self.save_warning='History could not be saved to disk.'
   return True
 def summary(self):
  with self._lock:points=list(self._points)
  comparable=len(points)>1 and 'dirs' in points[-2] and points[-2].get('scope')==points[-1].get('scope')
  return {'points':[{k:p[k] for k in ['finished','used','free','total']} for p in points],'changes':_changes(points[-2],points[-1]) if comparable else [],'since':points[-2]['finished'] if len(points)>1 else None,'comparable':comparable,'coverageNote':'Folder changes compare complete locations present in both scans. Newly indexed, missing or partially readable folders are not claimed as exact growth.','saveWarning':self.save_warning}
