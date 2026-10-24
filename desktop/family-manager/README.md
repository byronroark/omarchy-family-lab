# Family Manager bar launcher

Opens the existing parent `~/.local/bin/family-time-widget`. Repeated clicks present its existing GTK application window. Uses Omarchy bar styling and theme; no policy operations, household configuration, keys or network addresses live in the launcher.

Install parent controls first, copy this directory to `~/.config/omarchy/plugins/community.family-lab.manager`, validate with `omarchy plugin validate`, and place it with `omarchy bar put community.family-lab.manager --after byronroark.streampip --section right` or another preferred placement. Back up shell.json first. Layout changes hot-reload.

To remove, remove the widget's bar entry and user plugin directory. Removing the launcher does not change child policy or uninstall controls. This is a separate local bar adapter, not an additional marketplace listing.
