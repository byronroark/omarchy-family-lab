# Optional Google homepage shortcut for Chromium

This local Manifest V3 extension redirects only top-level visits to the bare `http(s)://google.com/` and `http(s)://www.google.com/` homepages to `https://www.google.com/safesearch`. It leaves search URLs, query-string searches, account pages and the SafeSearch page unchanged. It contains no JavaScript, remote code, history, cookie or all-site permissions.

It is a convenience shortcut, not SafeSearch enforcement. Keep the separately verified DNS/browser enforcement. It applies only to the browser installation where it is loaded, not automatically to Pi-hole groups. The user can disable a locally loaded extension.

An administrator can place these JSON files in a root-owned `/usr/local/share/family-lab/google-home-redirect` directory. Add that path to the existing comma-separated `--load-extension=` argument in the learner's Chromium flags file; preserve other extension paths and flags. Back up before editing. Fully exit Chromium and reopen it; closing one window may leave the existing browser running.

The master enrollment wizard does not currently install this optional shortcut. Isolated Chromium verification reached “Your SafeSearch Setting”; the existing household browser activation is still being diagnosed.
