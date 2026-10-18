"""Bounded client for the pinned forced SSH decision endpoint; never uses sudo."""
import json,os,select,subprocess,time
from family_approval import MAX_WIRE

def rpc(config,operation):
    if not (config.get('capability','technical')=='approver' or (config.get('capability','technical')=='technical' and config.get('quick_approval') is True)):raise ValueError('Scoped approval access is not enrolled')
    command=['/usr/bin/ssh','-F',config['ssh_config'],'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','-o','ConnectionAttempts=1','-T',config['approval_alias']]
    wire=json.dumps(operation,separators=(',',':'),ensure_ascii=True).encode()+b'\n'
    if len(wire)>MAX_WIRE:raise ValueError('Approval request is too large')
    with subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL) as proc:
        raw=b'';deadline=time.monotonic()+45
        try:
            proc.stdin.write(wire);proc.stdin.close()
            while True:
                left=deadline-time.monotonic()
                if left<=0 or not select.select([proc.stdout],[],[],left)[0]:raise ValueError('Approval service timed out; refresh before trying again')
                block=os.read(proc.stdout.fileno(),min(4096,MAX_WIRE+1-len(raw)))
                if not block:break
                raw+=block
                if len(raw)>MAX_WIRE:raise ValueError('Oversized approval response')
            if proc.wait(timeout=2):raise ValueError('Approval service unavailable; ask the technical helper')
        finally:
            if proc.poll() is None:proc.kill()
    response=json.loads(raw)
    if not isinstance(response,dict) or response.get('ok') is not True:raise ValueError(response.get('error','Approval was not accepted') if isinstance(response,dict) else 'Invalid approval response')
    return response

def decision(config,review,choice):
    if choice not in ('approve','deny'):raise ValueError('Invalid choice')
    return rpc(config,{'op':'decide','id':review['id'],'review':review['review'],'digest':review['digest'],'decision':choice})
