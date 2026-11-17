# LLM usage



All prompts are in this folder, in order:
- `01_initial_prompt.md` - the assignment text I gave the LLM.
- Add any follow-up prompts as `02_...md`, `03_...md`.

## How I validated the output
- Read and understood every file; scoring rules checked by hand against `model_v1.json` / `model_v2.json`.
- Ran `python -m unittest discover -s tests -v` (all pass) and `ruff check .`.
- Ran `docker compose up --build`, then exercised every endpoint with curl.
- Verified the audit file contains no raw email (only the sha256) and that tokens/emails are redacted in logs.
- Verified rollback: edit `active_model_version`, `POST /model/reload`, confirm version + checksum change.
- Verified the model file checksum equals `sha256sum model_artifacts/model_v1.json`.
