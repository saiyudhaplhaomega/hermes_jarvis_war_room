# War Room — How To

Diataxis category: **how-to** (problem-oriented, step by step).

## How to add a new API route
1. Add the route to the relevant `backend/api/<domain>.py` file.
2. Add a `(methods, path)` entry to `EXPECTED_ROUTE_POLICY` in `backend/core/route_policy.py`.
3. Use `Depends(get_current_user)` for protected routes; use `get_current_user_cookie_only` for SSE/EventSource.
4. Run `pytest tests/test_security_batch_a.py::test_route_policy_exact_allowlist_matches_registered_routes -q`.
5. If the route is high-stakes, write a Decision Brief under `decisions/` first.

## How to wire an SSE consumer
1. Frontend: POST `/sse-session` with `credentials: 'same-origin'`, then `new EventSource(url, { withCredentials: true })`.
2. Never construct `?token=...` URLs — the backend returns 401 and logs `sse_token_url_rejected`.
3. Always close the `EventSource` in component cleanup.

## How to run the release gate
1. Re-run tests: `venv/bin/python -m pytest tests/ -q`.
2. Re-run frontend build: `cd frontend-react && npm run build`.
3. Run IRON LAW: `python -m ops.iron_law` (writes evidence to `state/release/iron-law.json`).
4. Run docs gate: `python -m ops.docs_coverage` — fails if tutorial/how-to/reference/explanation are missing.
5. Validate the release report: `python -m ops.release --report path/to/report.json`.

## How to add a release-report artifact
1. Compute `sha256sum` of the artifact.
2. Append `{ "path": "...", "sha256": "..." }` to the report.
3. Re-run the validator.
