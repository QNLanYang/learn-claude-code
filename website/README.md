# Documentation Website

This directory contains the Docusaurus site shell for the repository docs.

The Markdown content stays in the repository-level content directories:

- `../docs`
- `../quick-start`
- `../references`
- `../glossary`
- `../diagrams`

## Local development

```bash
cd website
npm install
npm run start
```

## Build

```bash
cd website
npm run build
```

The static site output is written to `website/build/`. The `html` branch is
intended to contain only that built static output for GitHub Pages.
