# Roadmap Studio v0.4

Privacy-safe Gantt release using the latest four ServiceNow Excel exports.

## Replace GitHub files
Upload all contents to the repository root, preserving `.github/workflows/deploy.yml`.
If the repository name is not `roadmap-studio`, change `base` in `vite.config.js`.

## Privacy approach
Actual source titles are excluded. Each source record receives a stable-in-this-build alias such as `Project FMS 23`. The real project number remains visible. Cross-pillar memberships show the originating pillar as an italic suffix, for example `Project FMS 23 *FMS*` on BI.

`public/privacy_mapping.csv` is included for internal verification. Remove it before deployment if the alias-to-number mapping itself should not be downloadable. The deployed UI does not load this CSV.
