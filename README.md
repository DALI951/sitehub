# SiteHub

Every site Dali has deployed — auto-detected in one place. PWA + Android APK.

## How detection works

- **Server sites:** `api/api.php` deployed to `modali.powerpme.com/sitehub/api.php`
  scans `/public_html` for folders with a landing `index.html`/`index.php`.
  Upload a new site → it appears on the next refresh. Optional `site.json`
  in any folder overrides `name` / `description` / `url` / `order` / `favicon` / `hide`.
- **GitHub Pages sites:** the API fetches `api.github.com/users/DALI951/repos`
  (cached 15 min server-side) and adds repos with `has_pages`.

## The app

- `www/` — vanilla JS PWA (dark cinema, one red accent). Fetch on load,
  localStorage cache, offline fallback, "NEW" badge on first-seen sites.
- SW is network-first (fresh data wins, cache is emergency fallback).
- `seed.json` — bundled snapshot used only when the API and cache both fail.

## APK

- Capacitor 8, `com.dali951.sitehub`, launcher icons via `scripts/gen-icons.py`.
- `.github/workflows/build-apk.yml`: every push builds `assembleDebug` and
  publishes/updates a GitHub Release with `sitehub-v<version>.apk`.
- Bump `version` in `package.json` for a new release.

## Deploy

```powershell
$env:SITEHUB_SFTP_PASS='...'; python scripts/deploy.py   # web + api + site.json overrides
```

Creds fallbacks: `DEKKAN_SFTP_PASS` → `DUOSCORE_SFTP_PASS` (same host/user).

Live: https://modali.powerpme.com/sitehub/ · Repo releases: https://github.com/DALI951/sitehub/releases