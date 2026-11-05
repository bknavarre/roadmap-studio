# Roadmap Studio v0.5
Built from the latest four ServiceNow exports using normalization rules from roadmunk_SN_transfer_v2.py.

## Deploy
Replace the repository contents with this package, preserving `.github/workflows/deploy.yml`. Commit to `main`; GitHub Actions will deploy the site.

## Implemented
- Permanent Cascade layout, one record per line
- State swimlanes, globally reorderable
- Start-date sorting inside every State
- Demand/Enhancement/Idea canonical roadmap States
- SWIS records excluded from Campus portfolios
- Python pillar/date/FY/status normalization
- Masked titles with project number and completion
- Originating-pillar suffix on impacted-pillar views
- All imported detail fields, descriptions, and ServiceNow deep links
- Dashboard pillar counts
