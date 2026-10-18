"""Shared, data-only Omarchy palette for unprivileged family popup windows."""
import pathlib,re,tomllib

def themed_css(css,home=None):
    home=pathlib.Path.home() if home is None else pathlib.Path(home)
    try:
        with (home/'.local/state/omarchy/current/theme/colors.toml').open('rb') as source:
            raw=source.read(32769)
        if len(raw)>32768:return css
        data=tomllib.loads(raw.decode())
        palette={key:value for key,value in data.items() if isinstance(value,str) and re.fullmatch(r'#[a-fA-F0-9]{6}',value)}
    except (OSError,ValueError,UnicodeError):return css
    roles={'#101820':'background','#d9e5ee':'foreground','#74e0c3':'accent','#91a5b5':'foreground','#70d5ff':'accent','#192733':'lighter_background','#edf6ff':'foreground','#3e586b':'muted','#20313e':'lighter_background','#e1edf5':'foreground','#425c70':'muted','#2a4252':'selection','#6b8090':'dark_foreground','#283b49':'muted','#183f3a':'selection','#95f5d7':'foreground','#58b99a':'accent','#ffb9a9':'red','#345266':'muted'}
    return re.sub(rb'#[a-fA-F0-9]{6}',lambda match:palette.get(roles.get(match.group().decode().lower(),''),match.group().decode()).encode(),css)

def install_theme(css):
    import gi
    gi.require_version('Gtk','4.0');gi.require_version('Gdk','4.0')
    from gi.repository import Gtk,Gdk,GLib
    provider=Gtk.CssProvider();previous=None
    def refresh():
        nonlocal previous
        value=themed_css(css)
        if value!=previous:provider.load_from_data(value);previous=value
        return True
    refresh()
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    GLib.timeout_add_seconds(2,refresh)
    return provider
