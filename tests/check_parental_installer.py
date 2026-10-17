#!/usr/bin/env python3
"""Stage real installer file writes in a temp tree; mock all account/service actions."""
import contextlib
import io
import os
from pathlib import Path
import pwd
import grp
import runpy
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

if os.getuid() == 0:
    raise SystemExit('Skip staged installer test as root: run under an unprivileged test account.')
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temporary:
    stage=Path(temporary)
    for d in ('etc/pam.d','etc/systemd/system','var/lib','usr/local'):
        (stage/d).mkdir(parents=True,exist_ok=True)
    original_pam='#%PAM-1.0\nauth include system-auth\naccount include system-auth\nsession include system-auth\n'
    (stage/'etc/pam.d/system-login').write_text(original_pam)
    def mapped(value):
        text=os.fspath(value)
        if text.startswith(('/etc/','/var/lib/','/usr/local/')):
            return stage/text.lstrip('/')
        return Path(value)
    real_stat=Path.stat;real_mkstemp=tempfile.mkstemp;real_copy=shutil.copyfile
    real_chmod=os.chmod;real_replace=os.replace
    def fake_stat(self,*args,**kwargs):
        result=real_stat(self,*args,**kwargs)
        if str(self).startswith(str(stage)):
            values=list(result);values[4]=0
            return os.stat_result(values)
        return result
    def mkstemp(*args,**kwargs):
        if kwargs.get('dir') is not None:
            kwargs['dir']=mapped(kwargs['dir'])
        return real_mkstemp(*args,**kwargs)
    def copy(src,dst,*args,**kwargs):return real_copy(mapped(src),mapped(dst),*args,**kwargs)
    def chmod(path,*args,**kwargs):return real_chmod(mapped(path),*args,**kwargs)
    def replace(src,dst,*args,**kwargs):return real_replace(mapped(src),mapped(dst),*args,**kwargs)
    def account(name):
        return SimpleNamespace(pw_uid=2101 if name=='child' else 2102,pw_gid=2101,pw_name=name)
    # Replace only the installer's Path name; imported policy helpers receive already-staged paths.
    source=(ROOT/'scripts/install-parental-controls').read_text().replace('from pathlib import Path','from pathlib import Path as RealPath\nPath = staged_path')
    arguments=['installer','--apply','--subject','child','--peer','study-pc','--browser','chromium','--enable-pam','--parent-account','fl-dad','--parent-label','Dad']
    oldmask=os.umask(0o077)
    try:
        with patch.object(Path,'stat',fake_stat),patch.object(tempfile,'mkstemp',mkstemp),patch.object(shutil,'copyfile',copy),patch.object(os,'chmod',chmod),patch.object(os,'replace',replace),patch.object(os,'geteuid',return_value=0),patch.object(os,'getgrouplist',return_value=[2101]),patch.object(pwd,'getpwnam',side_effect=account),patch.object(grp,'getgrgid',return_value=SimpleNamespace(gr_name='child')),patch.object(grp,'getgrnam',return_value=SimpleNamespace(gr_gid=2104)),patch.object(subprocess,'run') as run,patch.object(sys,'argv',arguments),contextlib.redirect_stdout(io.StringIO()):
            exec(compile(source,str(ROOT/'scripts/install-parental-controls'),'exec'),{'__file__':str(ROOT/'scripts/install-parental-controls'),'staged_path':mapped,'__name__':'__main__'})
            calls=[item.args[0] for item in run.call_args_list]
            assert calls==[['/usr/bin/usermod','-a','-G','family-lab-parents','fl-dad'],['/usr/bin/systemctl','daemon-reload']],calls
    finally:
        os.umask(oldmask)
    import json
    policy=json.loads((stage/'var/lib/family-lab/policy.json').read_text())
    assert policy['policy']['subjects']['study-pc']['mode']=='off'
    assert not policy['policy']['subjects']['study-pc']['browser']['enabled']
    assert (stage/'etc/family-lab/system-login.before-family-lab').read_text()==original_pam
    assert (stage/'etc/pam.d/system-login').read_text().count('family-lab-policy login-check')==1
    assert (stage/'usr/local/libexec/family-lab-policy').stat().st_mode & 0o777==0o755
    assert (stage/'etc/chromium/policies/managed').stat().st_mode & 0o777==0o755
    assert (stage/'etc/family-lab').stat().st_mode & 0o777==0o755
    assert (stage/'var/lib/family-lab/policy.json').stat().st_mode & 0o077==0
print('PASS: staged installer writes, modes, PAM backup/gate, disabled defaults and fixed account/service actions; no live system changes')
