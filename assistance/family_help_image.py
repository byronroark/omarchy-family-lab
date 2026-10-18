"""Bounded local PNG handling. No SVG, URLs, shell commands or arbitrary attachment paths."""
import hashlib,io,os,pathlib,select,stat,struct,subprocess,time,zlib
MAX_IMAGE=6*1024*1024
MAX_SIDE=4096
MAX_PIXELS=12_000_000
def bounded_file(path,limit=MAX_IMAGE):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as file:
        if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):raise ValueError('Screenshot must be a regular PNG file')
        data=file.read(limit+1)
    if len(data)>limit:raise ValueError('Screenshot is too large (maximum 6 MB)')
    return data
def bounded_command(command,limit=MAX_IMAGE,seconds=12):
    with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL) as proc:
        data=b'';deadline=time.monotonic()+seconds
        try:
            while True:
                left=deadline-time.monotonic()
                if left<=0 or not select.select([proc.stdout],[],[],left)[0]:raise ValueError('Screenshot transfer timed out')
                chunk=os.read(proc.stdout.fileno(),min(65536,limit+1-len(data)))
                if not chunk:break
                data+=chunk
                if len(data)>limit:raise ValueError('Screenshot is too large (maximum 6 MB)')
            if proc.wait(timeout=2):raise ValueError('No PNG screenshot was available')
        finally:
            if proc.poll() is None:proc.kill()
    return data
def normalize_png(data):
    if not 33<=len(data)<=MAX_IMAGE or data[:16]!=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR':raise ValueError('Paste a PNG screenshot')
    if zlib.crc32(data[12:29]) & 0xffffffff != struct.unpack('>I',data[29:33])[0]:raise ValueError('Screenshot header is damaged')
    width,height=struct.unpack('>II',data[16:24])
    if not 1<=width<=MAX_SIDE or not 1<=height<=MAX_SIDE or width*height>MAX_PIXELS:raise ValueError('Screenshot is too large; capture a smaller region')
    # Do not allow animated PNGs, trailing payloads or unbounded chunk counts.
    offset=8;chunks=0;ended=False;clean=bytearray(data[:8])
    while offset<len(data):
        if offset+12>len(data):raise ValueError('Truncated screenshot')
        size=struct.unpack('>I',data[offset:offset+4])[0];kind=data[offset+4:offset+8]
        if size>MAX_IMAGE or offset+12+size>len(data):raise ValueError('Invalid screenshot chunk')
        if kind==b'acTL':raise ValueError('Use a still screenshot')
        chunk=data[offset+4:offset+8+size]
        if zlib.crc32(chunk)&0xffffffff!=struct.unpack('>I',data[offset+8+size:offset+12+size])[0]:raise ValueError('Screenshot is damaged')
        if kind in (b'IHDR',b'PLTE',b'tRNS',b'IDAT',b'IEND'):clean.extend(data[offset:offset+12+size])
        elif not kind[0]&32:raise ValueError('Unsupported screenshot data')
        offset+=12+size;chunks+=1
        if chunks>4096:raise ValueError('Screenshot contains too many chunks')
        if kind==b'IEND':ended=True;break
    if not ended or offset!=len(data):raise ValueError('Screenshot has unexpected extra data')
    import gi
    gi.require_version('GdkPixbuf','2.0')
    from gi.repository import GdkPixbuf
    loader=GdkPixbuf.PixbufLoader.new_with_type('png')
    try:loader.write(bytes(clean));loader.close();pixbuf=loader.get_pixbuf()
    except Exception as exc:raise ValueError('Could not decode the screenshot') from exc
    if pixbuf is None or (pixbuf.get_width(),pixbuf.get_height())!=(width,height):raise ValueError('Invalid screenshot dimensions')
    ok,encoded=pixbuf.save_to_bufferv('png',[],[])
    if not ok or len(encoded)>MAX_IMAGE:raise ValueError('Screenshot is too large after cleaning')
    encoded=bytes(encoded)
    return encoded,{'sha256':hashlib.sha256(encoded).hexdigest(),'bytes':len(encoded),'width':width,'height':height}
def prune(folder,keep=8):
    import re
    folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    files=sorted((p for p in folder.glob('*.png') if re.fullmatch('[a-f0-9]{32}\\.png',p.name)),key=lambda p:p.lstat().st_mtime)
    count=len(files)
    for path in files:
        if count>keep or time.time()-path.lstat().st_mtime>86400:
            path.unlink(missing_ok=True)
            count-=1
