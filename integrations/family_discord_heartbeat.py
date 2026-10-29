"""Forced SSH heartbeat; one fixed parent, no command or caller-controlled paths."""
import json,os,stat,sys,time
if os.environ.get('SSH_ORIGINAL_COMMAND') or os.isatty(0):sys.exit(1)
if sys.stdin.buffer.read(129)!=b'{"online":true}\n':sys.exit(1)
path='/var/lib/family-discord-heartbeat/parent.json'
fd=os.open(path,os.O_WRONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
info=os.fstat(fd)
if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1:sys.exit(1)
with os.fdopen(fd,'w') as file:
 file.write(json.dumps({'seen':time.time()}));file.truncate();file.flush();os.fsync(file.fileno())
print('{"ok":true}')
