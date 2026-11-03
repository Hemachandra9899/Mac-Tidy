"""Conservative local personal-file scope for age and duplicate review."""
import stat
from pathlib import Path
from ..rules.policy import PACKAGE_SUFFIXES
PERSONAL=('Documents','Downloads','Desktop')
EXCLUDED={'node_modules','venv','.venv','__pycache__','site-packages','Library'}
DATALESS=0x40000000  # Darwin SF_DATALESS: content is not locally materialized.
def personal_path(path,home):
 try:parts=Path(path).relative_to(Path(home)).parts
 except ValueError:return False
 return len(parts)>1 and parts[0] in PERSONAL and not any(p.startswith('.') or p in EXCLUDED or p.lower().endswith(PACKAGE_SUFFIXES) for p in parts) and not str(path).lower().endswith(('.icloud','.download','.crdownload','.part'))
def local_regular(st):
 return stat.S_ISREG(st.st_mode) and not getattr(st,'st_flags',0)&DATALESS and (st.st_size==0 or st.st_blocks>0)
