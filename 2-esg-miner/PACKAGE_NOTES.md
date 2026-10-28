# Code Package Notes

This package contains the ESG selective MinerU extraction system source code, configuration templates, frontend source, tests, deployment files, and selected technical documentation.

Excluded from this package: local secrets (.env), uploaded/source data, extraction outputs, caches, node_modules, frontend build outputs, LaTeX intermediate files, and temporary files.

Quick start:
1. Copy configs/.env.example to .env and fill model/database settings.
2. Install Python dependencies from pyproject.toml / requirements-mineru.txt.
3. Install frontend dependencies under frontend-react if developing the UI.
4. See README.md and docs/technical_manual.pdf for full usage details.
