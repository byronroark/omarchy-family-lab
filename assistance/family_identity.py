"""Display identity only; helper selection never grants administrator access."""
import json,pathlib

def helper_config(home=None):
    folder=(pathlib.Path.home() if home is None else pathlib.Path(home))/'.config/family-help'
    path=folder/'helper.json'
    if not path.exists():path=folder/'dad.json'  # Existing verified installations.
    return json.loads(path.read_text())

def identity(config):
    label=config.get('helper_label','Dad');slug=config.get('helper_slug','dad')
    if not isinstance(label,str) or not 1<=len(label)<=40 or not all(c.isprintable() for c in label):raise ValueError('Invalid helper display label')
    if slug not in ('dad','mom','parent'):raise ValueError('Invalid helper role')
    return label,slug
