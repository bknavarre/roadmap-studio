# Roadmap Studio v0.2 - GitHub Pages

This package is configured for a GitHub repository named `roadmap-studio`.

## Upload
Upload the CONTENTS of this folder to the root of the GitHub repository, preserving the folder structure, especially:

- `.github/workflows/deploy.yml`
- `public/roadmap_import.csv`
- `src/main.jsx`
- `src/style.css`

## Enable GitHub Pages
1. Open repository Settings.
2. Select Pages.
3. Under Build and deployment, choose Source: GitHub Actions.
4. Open Actions and run `Deploy Roadmap Studio to GitHub Pages`, or make any commit to `main`.

Expected URL:
`https://YOUR-GITHUB-USER.github.io/roadmap-studio/`

## Different repository name
If the repository is not exactly `roadmap-studio`, edit `vite.config.js` and change:
`base: '/roadmap-studio/'`
to:
`base: '/YOUR-REPOSITORY-NAME/'`
