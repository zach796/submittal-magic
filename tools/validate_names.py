import re, sys
ICON_RE = re.compile(r'^ICON-(\d{6})-([A-Z0-9\-]+)(?:-([A-Z0-9\-]+))?\.(svg|png|pdf)$')
SPEC_RE = re.compile(r'^(USA)-([A-Z]{2})-(\d{3})-([12])-([0-9]{6})-([0-9]{6})-([A-Za-z0-9\-]+)-([A-Za-z0-9\-]+)\.pdf$')
for name in sys.stdin:
    n = name.strip()
    if not n: continue
    if ICON_RE.match(n): print(f'ICON OK  → {n}')
    elif SPEC_RE.match(n): print(f'SPEC OK  → {n}')
    else: print(f'FAIL     → {n}')
