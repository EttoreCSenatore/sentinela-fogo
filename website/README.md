# Sentinela do Fogo: documentation

Docusaurus site, English (default) and Brazilian Portuguese.

```bash
npm install
npm start                      # English, http://localhost:3000/sentinela-fogo/
npm start -- --locale pt-BR    # Portuguese
npm run build                  # both locales into build/
```

- English pages: `docs/`
- Portuguese pages: `i18n/pt-BR/docusaurus-plugin-content-docs/current/` (same file names)
- UI labels: `i18n/pt-BR/*.json` (`npm run write-translations -- --locale pt-BR` after adding navbar/sidebar items)

Every change to a page in `docs/` should be made in the pt-BR copy too.
Pushes to `main` deploy to GitHub Pages (`.github/workflows/docs.yml`).
