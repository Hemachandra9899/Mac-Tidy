"""Older personal files: modification age is evidence, never proof of disuse."""
from ..common.paths import personal_path
MIN_BYTES=1_000_000
MIN_DAYS=90
def review_inventory(report):
 if 'reviewFiles' in report:return report['reviewFiles'],'review-file'
 return report.get('files',[]),'file'
def older_files(report,now):
 rows,kind=review_inventory(report);found=[]
 for index,row in enumerate(rows):
  if row.get('size',0)<MIN_BYTES or not personal_path(row['path'],report['home']):continue
  age=max(0,int((now-row['mtime'])//86400))
  if age<MIN_DAYS:continue
  found.append({**row,'index':index,'type':kind,'ageDays':age})
 found.sort(key=lambda r:r['size'],reverse=True)
 return {'files':found,'ageBasis':'modified','minDays':MIN_DAYS,'indexedFiles':len(rows),'scope':'Local indexed personal files of at least 1 MB. Modification age does not prove a file is unused.'}
