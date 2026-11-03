"""Explicit, bounded duplicate searches over local personal files.

Content is read only after start(). Equal sizes/edge samples are candidates;
full SHA-256 hashes confirm matches. Changed, symlinked, nonlocal, hard-linked
and package files are excluded. No file is moved here.
"""
import hashlib,os,stat,threading,time
from pathlib import Path
from ..common.paths import personal_path,local_regular
from ..cleanup.fingerprint import fingerprint
MIN_FILE_BYTES=1_000_000
CHUNK_BYTES=1<<20
EDGE_BYTES=64*1024
DEFAULT_BUDGET=2_000_000_000
MAX_BUDGET=32_000_000_000
MAX_FOLDER_ENTRIES=10000
MAX_FOLDER_GROUPS=100
class Skipped(Exception):pass
class Cancelled(Exception):pass
class Budget(Exception):pass

def _open(path):
 if str(Path(path).resolve(strict=True))!=str(Path(path).absolute()):raise Skipped('symlink')
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 f=os.fdopen(fd,'rb')
 if not local_regular(os.fstat(f.fileno())):f.close();raise Skipped('not a local regular file')
 return f

def stable_hash(path,on_bytes=lambda n:None,cancel=lambda:False,max_bytes=None):
 with _open(path) as f:
  before=os.fstat(f.fileno());digest=hashlib.sha256();consumed=0
  if max_bytes is not None and before.st_size>max_bytes:raise Budget()
  while consumed<before.st_size:
   if cancel():raise Cancelled()
   chunk=f.read(min(CHUNK_BYTES,before.st_size-consumed))
   if not chunk:raise Skipped('truncated during hashing')
   digest.update(chunk);consumed+=len(chunk);on_bytes(len(chunk))
  after=os.fstat(f.fileno())
  expected=(before.st_dev,before.st_ino,before.st_mtime_ns,before.st_size)
  actual=(after.st_dev,after.st_ino,after.st_mtime_ns,after.st_size)
  if expected!=actual or fingerprint(path)!=list(expected):raise Skipped('changed during hashing')
  return digest.hexdigest(),list(expected)

def _quick(path,size):
 with _open(path) as f:
  before=os.fstat(f.fileno());head=f.read(EDGE_BYTES);f.seek(max(0,size-EDGE_BYTES));tail=f.read(EDGE_BYTES)
  if before.st_size!=size:raise Skipped('size changed')
  return hashlib.blake2b(head+tail,digest_size=16).digest()

def _group(items,key):
 groups={}
 for item in items:
  try:groups.setdefault(key(item),[]).append(item)
  except (OSError,ValueError,Skipped):continue
 return [g for g in groups.values() if len(g)>1]

class DuplicateFinder:
 def __init__(self):
  self._lock=threading.Lock();self._state={'status':'idle','groups':[]};self._cancel=threading.Event()
 def status(self):
  with self._lock:return dict(self._state)
 def reset(self):
  with self._lock:
   if self._state['status']!='running':self._state={'status':'idle','groups':[]}
 def mark_moved(self,path):
  with self._lock:
   if self._state.get('status')!='complete' or self._state.get('mode')!='files':return
   groups=[]
   for group in self._state.get('groups',[]):
    files=[f for f in group['files'] if f['path']!=path]
    if len(files)<2:continue
    groups.append({**group,'files':files,'keeper':files[0]['index'],'wasted':sum(f['logical'] for f in files[1:]),'allocatedEstimate':sum(f['size'] for f in files[1:])})
   self._state={**self._state,'groups':groups,'wasted':sum(g['wasted'] for g in groups)}
 def cancel(self):self._cancel.set();return {'cancelRequested':True}
 def _update(self,**fields):
  with self._lock:self._state.update(fields)
 def _progress(self,n):
  with self._lock:self._state['bytesHashed']=self._state.get('bytesHashed',0)+n
 def start(self,files,revision,*,home,mode='files',report=None,budget=DEFAULT_BUDGET):
  with self._lock:
   if self._state['status']=='running':return False
   self._cancel.clear();self._state={'status':'running','revision':revision,'mode':mode,'groups':[],'bytesHashed':0,'budget':budget}
  target=self._run_folders if mode=='folders' else self._run
  args=(report,revision) if mode=='folders' else (files,revision)
  threading.Thread(target=target,args=args,kwargs={'home':home,'budget':budget},daemon=True).start();return True
 def _begin(self,revision,mode,budget):
  self._update(status='running',revision=revision,mode=mode,groups=[],bytesHashed=0,budget=budget,skippedBudget=0,skippedChanged=0)
 def _run(self,files,revision,*,home,budget=DEFAULT_BUDGET):
  started=time.time();self._begin(revision,'files',budget);skipped=0;changed=0;checked=[];seen=set();spent=0
  try:
   for row in files:
    if self._cancel.is_set():raise Cancelled()
    if row.get('logical',0)<MIN_FILE_BYTES or not personal_path(row['path'],home):continue
    try:
     st=os.lstat(row['path']);identity=(st.st_dev,st.st_ino)
     if not local_regular(st) or identity in seen or st.st_size!=row['logical']:continue
     if 'mtime' in row and abs(st.st_mtime-row['mtime'])>.00001:continue
     if 'mtimeNs' in row and st.st_mtime_ns!=row['mtimeNs']:continue
     seen.add(identity);checked.append(row)
    except OSError:changed+=1
   same_size=_group(checked,lambda f:f['logical'])
   groups=[]
   for candidates in same_size:
    if self._cancel.is_set():raise Cancelled()
    # Edge reads also count toward the declared I/O budget.
    edge_cost=sum(min(f['logical'],2*EDGE_BYTES) for f in candidates)
    if spent+edge_cost>budget:skipped+=len(candidates);continue
    edges=_group(candidates,lambda f:_quick(f['path'],f['logical']));spent+=edge_cost;self._progress(edge_cost)
    for edge_group in edges:
     cost=sum(f['logical'] for f in edge_group)
     if spent+cost>budget:skipped+=len(edge_group);continue
     hashes={}
     for f in edge_group:
      try:
       digest,fp=stable_hash(f['path'],self._progress,self._cancel.is_set,max_bytes=budget-self.status()['bytesHashed']);hashes.setdefault(digest,[]).append({**f,'fingerprint':fp})
      except Budget:skipped+=1
      except (OSError,ValueError,Skipped):changed+=1
     spent=self.status()['bytesHashed']
     for digest,matches in hashes.items():
      if len(matches)<2:continue
      matches.sort(key=lambda f:(f.get('mtime',0),f['path']))
      groups.append({'id':digest,'sha256':digest,'size':matches[0]['logical'],'wasted':sum(f['logical'] for f in matches[1:]),'allocatedEstimate':sum(f['size'] for f in matches[1:]),'files':matches,'keeper':matches[0]['index']})
   groups.sort(key=lambda g:g['wasted'],reverse=True)
   self._update(status='complete',groups=groups,wasted=sum(g['wasted'] for g in groups),filesChecked=len(checked),skippedBudget=skipped,skippedChanged=changed,elapsed=round(time.time()-started),scope='Indexed local personal files of at least 1 MB. Hard links, packages and dependency trees excluded. APFS shared blocks may reduce actual savings.')
  except Cancelled:self._update(status='cancelled',groups=[],elapsed=round(time.time()-started))
  except Exception as ex:self._update(status='error',groups=[],message=str(ex))
 def _folder_manifest(self,path,home,budget):
  digest=hashlib.sha256();entries=0;read=0;allocated=0;stack=[Path(path)];manifest=[]
  while stack:
   directory=stack.pop()
   if not personal_path(str(directory),home):raise Skipped('excluded directory')
   before=fingerprint(str(directory));manifest.append((str(directory),before))
   with os.scandir(directory) as scan:children=sorted(list(scan),key=lambda e:e.name)
   for child in children:
    if self._cancel.is_set():raise Cancelled()
    entries+=1
    if entries>MAX_FOLDER_ENTRIES:raise Skipped('folder entry limit')
    if child.is_symlink() or not personal_path(child.path,home):raise Skipped('folder contains excluded entries')
    relative=str(Path(child.path).relative_to(path));st=child.stat(follow_symlinks=False)
    if stat.S_ISDIR(st.st_mode):digest.update(b'D\0'+relative.encode()+b'\0');stack.append(Path(child.path))
    elif local_regular(st):
     if read+st.st_size>budget:raise Budget()
     if self.status().get('bytesHashed',0)+st.st_size>self.status()['budget']:raise Budget()
     value,fp=stable_hash(child.path,self._progress,self._cancel.is_set,max_bytes=min(budget-read,self.status()['budget']-self.status()['bytesHashed']));read+=st.st_size;allocated+=st.st_blocks*512
     digest.update(b'F\0'+relative.encode()+b'\0'+str(st.st_size).encode()+b'\0'+value.encode()+b'\0');manifest.append((child.path,fp))
    else:raise Skipped('unsupported or nonlocal entry')
  for item,fp in manifest:
   if fingerprint(item)!=fp:raise Skipped('folder changed')
  return digest.hexdigest(),read,allocated
 def _run_folders(self,report,revision,*,home,budget=DEFAULT_BUDGET,min_bytes=MIN_FILE_BYTES):
  started=time.time();self._begin(revision,'folders',budget);spent=0;skipped=0;changed=0;verified=[]
  try:
   candidates=[d for d in report['dirs'] if personal_path(d['path'],home) and not d.get('partial') and d.get('logical',d['size'])>=min_bytes]
   size_groups=_group(candidates,lambda d:d.get('logical',d['size']))
   size_groups.sort(key=lambda g:g[0].get('logical',g[0]['size']),reverse=True)
   for group in size_groups[:MAX_FOLDER_GROUPS]:
    matches={}
    for d in group:
     if self._cancel.is_set():raise Cancelled()
     # A folder containing another candidate cannot be equal to its nonempty child.
     try:
      estimate=d.get('logical',d['size'])
      if spent+estimate>budget:skipped+=1;continue
      digest,used,allocated=self._folder_manifest(d['path'],home,budget-spent);spent+=used
      matches.setdefault(digest,[]).append({**d,'allocatedEstimate':allocated})
     except Budget:skipped+=1;spent=budget
     except (OSError,ValueError,Skipped):changed+=1
     spent=self.status().get('bytesHashed',spent)
    for digest,folders in matches.items():
     if len(folders)>1:
      folders.sort(key=lambda d:d['path']);verified.append({'id':digest,'size':folders[0].get('logical',folders[0]['size']),'folders':folders,'wasted':sum(d.get('logical',d['size']) for d in folders[1:])})
   # Nested duplicate groups are useful for browsing, but count their bytes once.
   verified.sort(key=lambda g:g['size'],reverse=True);groups=[];covered=[]
   for group in verified:
    if all(any(d['path'].startswith(parent+'/') for parent in covered) for d in group['folders']):continue
    groups.append(group);covered.extend(d['path'] for d in group['folders'])
   self._update(status='complete',groups=groups,wasted=sum(g['wasted'] for g in groups),foldersChecked=sum(len(g) for g in size_groups[:MAX_FOLDER_GROUPS]),skippedBudget=skipped,skippedChanged=changed,elapsed=round(time.time()-started),scope=f'Complete personal folders with matching measured sizes; maximum {MAX_FOLDER_GROUPS} candidate groups and {MAX_FOLDER_ENTRIES:,} entries per folder. Full relative names and contents verified. Folder results are inspect-only.')
  except Cancelled:self._update(status='cancelled',groups=[],elapsed=round(time.time()-started))
  except Exception as ex:self._update(status='error',groups=[],message=str(ex))
