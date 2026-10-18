"""Launch a root-owned Wayland guard as its isolated, unprivileged system UID.

The UI receives no administrator key, sudo rights or power-operation capability.
"""
import json,os,pathlib,pwd,socket,stat,struct,subprocess,time
class Guards:
    def __init__(self,config):self.config=config;self.processes={};self.errors={};self.last_attempt={}
    def covering(self,peer):
        process=self.processes.get(peer)
        return process is not None and process.poll() is None
    def sync(self,status):
        for peer,row in status.items():
            guard=[int(uid) for uid,value in self.config.get('guards',{}).items() if value==peer]
            process=self.processes.get(peer)
            if not row.get('logged_in'):
                if process and process.poll() is None:process.terminate()
                self.processes.pop(peer,None);continue
            if not guard or row['mode']!='enforce' or not row['blocked']:continue
            if process and process.poll() is None:continue
            if time.monotonic()-self.last_attempt.get(peer,-1000)<5:continue
            self.last_attempt[peer]=time.monotonic()
            try:
                if len(guard)!=1:raise ValueError('Exactly one isolated guard account is required')
                uid=guard[0];account=pwd.getpwuid(uid)
                if not 0<uid<1000 or uid==row['uid']:raise ValueError('Guard must be a separate system UID')
                directory=pathlib.Path('/run/user')/str(row['uid']);info=directory.lstat()
                if not stat.S_ISDIR(info.st_mode) or info.st_uid!=row['uid'] or info.st_mode&0o022:raise ValueError('Unsafe learner Wayland directory')
                sockets=[path for path in directory.glob('wayland-*') if stat.S_ISSOCK(path.lstat().st_mode) and path.lstat().st_uid==row['uid']]
                if len(sockets)!=1:raise ValueError('Cannot identify a unique learner Wayland socket')
                runtime=pathlib.Path('/run/family-lab-guard')/str(uid)
                if runtime.exists():
                    info=runtime.lstat()
                    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=uid or info.st_mode&0o077:raise ValueError('Unsafe guard runtime')
                else:runtime.mkdir(mode=0o700);os.chown(runtime,uid,account.pw_gid)
                env={'HOME':str(runtime),'XDG_RUNTIME_DIR':str(runtime),'XDG_CONFIG_HOME':str(runtime/'config'),'XDG_CACHE_HOME':str(runtime/'cache'),'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','QT_QPA_PLATFORM':'wayland','QT_QPA_PLATFORMTHEME':'basic','QT_QUICK_BACKEND':'software','QT_QUICK_CONTROLS_STYLE':'Basic'}
                # Connect first and pass the descriptor. Never change ACLs on a
                # child-owned pathname that could be swapped for a symlink.
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
                    connection.settimeout(3);connection.connect(str(sockets[0]));connection.settimeout(None)
                    pid,peer_uid,_=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    binary=pathlib.Path('/proc')/str(pid)/'exe';actual=binary.resolve(strict=True)
                    if peer_uid!=row['uid'] or actual not in (pathlib.Path('/usr/bin/Hyprland'),pathlib.Path('/usr/bin/hyprland')) or actual.stat().st_uid!=0 or actual.stat().st_mode&0o022:raise ValueError('Wayland socket is not the enrolled native Hyprland compositor')
                    env['WAYLAND_SOCKET']=str(connection.fileno())
                    self.processes[peer]=subprocess.Popen(['/usr/bin/setpriv','--reuid='+str(uid),'--regid='+str(account.pw_gid),'--init-groups','--no-new-privs','/usr/bin/quickshell','--no-color','-p','/usr/local/share/family-lab/guard'],env=env,cwd='/',stdin=subprocess.DEVNULL,close_fds=True,pass_fds=(connection.fileno(),))
                self.errors.pop(peer,None)
            except (OSError,ValueError,subprocess.SubprocessError) as exc:self.errors[peer]=str(exc)[:300]
