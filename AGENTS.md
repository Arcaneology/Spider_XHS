# Repository Guidelines

## Project Structure & Module Organization
The entry point is `main.py`, which wires `apis/xhs_pc_apis.py` and `apis/xhs_creator_apis.py` into the orchestration logic. Helpers under `xhs_utils/` cover cookie handling, downloading, and Excel export, so place new utilities there rather than duplicating code inside the API layer. Browser-signature scripts live in `static/` and are consumed via `PyExecJS`; keep them versioned alongside any matching Node helpers defined in `package.json`. Media placeholders, QR codes, and sponsorship art stay under `author/`. Add new assets or fixtures in directories that match their runtime consumers to keep Docker builds deterministic.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` installs Python dependencies such as `loguru`, `requests`, and `openpyxl`.
- `npm install` pulls in the minimal Node runtime (`jsdom`) required by `PyExecJS` when evaluating the `static/*.js` signatures.
- `python main.py` executes the default crawler flow after `COOKIES` (and optional proxy settings) are added to `.env`.
- `docker build -t spider_xhs .` and `docker run --env-file .env spider_xhs` provide a reproducible runtime without polluting the host environment.

## Coding Style & Naming Conventions
Follow PEP 8: 4-space indentation, snake_case functions, and PascalCase classes (see `Data_Spider`). Annotate public methods with type hints, keep docstrings bilingual-friendly, and log operational steps with `loguru` rather than `print`. Name new modules after the surface they wrap (`xhs_utils/note_util.py`, `apis/xhs_mobile_apis.py`, etc.) and mirror the directory casing already in the repo.

## Testing Guidelines
There is no committed automated suite yet, so add targeted regression tests whenever touching parsing logic. Prefer `pytest` under a new `tests/` package, mirroring the runtime modules (`tests/test_data_util.py`, `tests/api/test_creator.py`). Use fixtures with sanitized cookies and point downloads at a throwaway directory. Run `pytest -k note` locally before raising a PR, and capture manual smoke results (CLI output, sample Excel) in the PR description.

## Commit & Pull Request Guidelines
Recent history follows Conventional Commits (`feat: 优化buildContentString函数…`), so keep the `<type>: <summary>` format and use English summaries when possible for searchability. Commits should be scoped to one feature or fix and include updates to docs or sample configs when behavior changes. Pull requests must describe the problem, the solution, reproduction steps, and any manual validation evidence (screenshots, redacted logs, Excel diffs). Link related issues and flag breaking API changes in the title. Never include real cookies or tokens in commits.

## Security & Configuration Tips
Treat `.env` as sensitive—store only temporary cookies, keep the file out of commits, and rotate credentials after testing. When sharing scripts, mask note IDs or use demo accounts. Proxy details should be injected via environment variables instead of hardcoding them inside `xhs_utils`.
