"""Fixed noninteractive app-install plans; updates/agents/drivers require a technician."""
import json,os,pathlib,pwd,subprocess
from family_approval import PACKAGE,PINNED,trusted
from family_software import validate_request
import family_menu
ENV={'HOME':'/root','USER':'root','LOGNAME':'root','PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TERM':'xterm-256color','OMARCHY_PATH':'/usr/share/omarchy'}
class Actions:
    def __init__(self,teaching,runner=subprocess.run):self.teaching=teaching;self.runner=runner
    def command(self,args,**kwargs):return self.runner(args,env=ENV,cwd='/root',stdin=subprocess.DEVNULL,close_fds=True,**kwargs)
    def poll(self):
        child=pwd.getpwnam(self.teaching['child'])
        if child.pw_uid<1000 or child.pw_name==self.teaching['admin']:raise ValueError('Invalid learner identity')
        args=['/usr/bin/setpriv','--reuid='+str(child.pw_uid),'--regid='+str(child.pw_gid),'--init-groups','--no-new-privs','/usr/bin/env','-i','HOME='+child.pw_dir,'USER='+child.pw_name,'PATH=/usr/bin:/bin','/usr/bin/python3','/usr/local/libexec/family-help-child','poll']
        # The child may change its endpoint output. Bound it before decoding.
        with subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=ENV,cwd='/') as proc:
            import select,time
            raw=b'';deadline=time.monotonic()+5
            try:
                while True:
                    left=deadline-time.monotonic()
                    if left<=0 or not select.select([proc.stdout],[],[],left)[0]:raise ValueError('Learner poll timed out')
                    block=os.read(proc.stdout.fileno(),2049-len(raw))
                    if not block:break
                    raw+=block
                    if len(raw)>2048:raise ValueError('Oversized learner request')
                if proc.wait(timeout=1):raise ValueError('Learner poll unavailable')
            finally:
                if proc.poll() is None:proc.kill()
        result=json.loads(raw)
        if not isinstance(result,dict):raise ValueError('Invalid learner request')
        if result and 'software' in result:validate_request(result)
        return result
    def plan(self,request,principal):
        validate_request(request);software=request['software'];scope=principal['scope']
        unsupported={'supported':False,'title':'Technical helper needed','reason':'This action is outside this parent’s delegated app-install permissions. No installer will run.','requested':software.get('packages',[]) or ([software['menu']] if 'menu' in software else []),'transaction':[]}
        if software['action']=='update':return dict(unsupported,reason='Omarchy updates and migrations need the technical helper in this release.')
        item=None
        if software['action']=='install':
            if any(package not in scope['packages'] for package in software['packages']):return unsupported
            names=software['packages'];title='Install repository packages'
        else:
            if software['menu'] not in scope['menus']:return unsupported
            trusted(family_menu.CATALOG)
            try:item,names=family_menu.plan(software['menu'])
            except (OSError,ValueError):return dict(unsupported,reason='The installed app helper changed or is unavailable; the technical helper must review it.')
            if item['mode'] not in ('package','script'):return unsupported
            title=item['title']
        try:
            result=self.command(['/usr/bin/pacman','-Sp','--needed','--noconfirm','--print-format','%r/%n=%v','--',*names],capture_output=True,text=True,timeout=30,check=True) if names else None
            transaction=result.stdout.splitlines() if result else []
            if len(transaction)>256 or any(not PINNED.fullmatch(value) for value in transaction):raise ValueError('Unexpected package transaction; technical review required')
            # Stable order/deduplication; full resolved dependency versions are reviewed.
            transaction=list(dict.fromkeys(transaction))
            return {'supported':True,'title':title,'reason':'Install only the displayed app and resolved package versions. No update, reboot or administrator shell.','requested':names,'transaction':transaction,'menu':software.get('menu'),'source':item}
        except (OSError,ValueError,subprocess.SubprocessError):return dict(unsupported,reason='Package resolution needs the technical helper. No installation is authorized.')
    def execute(self,request,plan):
        if not plan['supported']:raise ValueError('Unsupported delegated action')
        if pathlib.Path('/var/lib/pacman/db.lck').exists():raise ValueError('Package manager is busy; ask again after it finishes')
        if any(not PINNED.fullmatch(value) for value in plan['transaction']):raise ValueError('Invalid pinned package transaction')
        if plan['transaction']:
            result=self.command(['/usr/bin/pacman','-S','--needed','--noconfirm','--',*plan['transaction']],timeout=1800)
            if result.returncode:return result.returncode
        if plan['menu']:
            item=plan['source'];family_menu.check_sources(item)
            if item.get('extra')=='lutris-python':
                target=pathlib.Path('/usr/bin/lutris');trusted(target)
                result=self.command(['/usr/bin/sed','-i','/env python3/ c\\#!/bin/python3',str(target)],timeout=30)
                if result.returncode:return result.returncode
            child=pwd.getpwnam(self.teaching['child'])
            if child.pw_uid<1000 or child.pw_name==self.teaching['admin']:raise ValueError('Invalid learner identity')
            # The existing fixed child phase has setpriv + --no-new-privs, clean env,
            # no agent/admin descriptors, and only the enrolled menu ID.
            result=self.command(family_menu.child_command(child,plan['menu']),timeout=300)
            return result.returncode
        return 0
