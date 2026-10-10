from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import urllib.request,json,hashlib
root=Path(__file__).parent
with ZipFile(root/'source.zip','w',ZIP_DEFLATED) as z:
    for p in root.rglob('*'):
        if p.is_file() and not any(v in {'exports','ephemeris-data','__pycache__','.git','.env'} for v in p.relative_to(root).parts) and p.suffix!='.zip':
            z.write(p,p.relative_to(root))
    # Include exact unmodified AGPL dependency source, not just wheel binaries.
    for package,version in [('kerykeion','6.0.5'),('libephemeris','3.2.2')]:
        with urllib.request.urlopen(f'https://pypi.org/pypi/{package}/{version}/json',timeout=60) as r:
            info=json.load(r)
        source=next(v for v in info['urls'] if v['packagetype']=='sdist')
        with urllib.request.urlopen(source['url'],timeout=120) as r:data=r.read()
        assert hashlib.sha256(data).hexdigest()==source['digests']['sha256']
        z.writestr('third-party-source/'+source['filename'],data)
