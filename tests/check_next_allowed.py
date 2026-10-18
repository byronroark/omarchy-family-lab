"""Calendar forecasts, including DST. No live policy/PAM/power operations."""
import datetime as dt
import importlib.machinery
import importlib.util
from pathlib import Path
from zoneinfo import ZoneInfo

loader=importlib.machinery.SourceFileLoader('forecast',str(Path(__file__).resolve().parents[1]/'parental/family-lab-policy'))
spec=importlib.util.spec_from_loader(loader.name,loader);m=importlib.util.module_from_spec(spec);loader.exec_module(m)
p=m.defaults(['study-pc']);p['subjects']['study-pc']['mode']='enforce'
u={'days':{},'grants':{}}
def stamp(value):return dt.datetime.fromisoformat(value).timestamp()
def forecast(value):return m.next_allowed(p,u,'study-pc',stamp(value))
assert forecast('2026-01-05T10:00:00+00:00')['at']==stamp('2026-01-05T10:00:00+00:00')
assert forecast('2026-01-05T22:00:00+00:00')['at']==stamp('2026-01-06T08:00:00+00:00')
u['days']={'2026-01-05':{'study-pc':5400}}
assert forecast('2026-01-05T10:00:00+00:00')['at']==stamp('2026-01-06T08:00:00+00:00')
u['grants']={'2026-01-05/study-pc':15}
assert forecast('2026-01-05T10:00:00+00:00')['at']==stamp('2026-01-05T10:00:00+00:00')
u={'days':{},'grants':{}}
p['subjects']['study-pc']['daily_minutes']={day:0 for day in m.DAYS}
assert forecast('2026-01-05T10:00:00+00:00') is None
# Spring-forward gap: nonexistent 02:30-02:45 has no permitted instant that day.
p=m.defaults(['study-pc']);p['timezone']='America/New_York';p['subjects']['study-pc']['mode']='enforce'
p['subjects']['study-pc']['hours']={day:[['02:30','02:45']] for day in m.DAYS}
result=forecast('2026-03-08T01:59:00-05:00')
assert result['at']==stamp('2026-03-09T02:30:00-04:00'),result
# Fall-back fold: a second 01:30 is a real allowed instant.
p['subjects']['study-pc']['hours']={day:[['01:30','01:45']] for day in m.DAYS}
result=forecast('2026-11-01T01:50:00-04:00')
assert result['at']==stamp('2026-11-01T01:30:00-05:00'),result
print('PASS: next permitted time, tomorrow after quota, grants, no availability and DST gap/fold')

from unittest.mock import patch
import subprocess
for answer,available in [('yes',True),('no',False),('challenge',False),('na',False),('unexpected',False)]:
    result=subprocess.CompletedProcess([],0,'s "'+answer+'"\n')
    with patch.object(m.subprocess,'run',return_value=result) as run:
        info=m.hibernation_capability()
        assert info['available']==available and not info['ready_for_family_lab']
        assert run.call_args.args[0][-1]=='CanHibernate'
print('PASS: read-only hibernation capability never enables sleep or claims resume readiness')
