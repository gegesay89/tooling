<<<<<<< HEAD
# tooling
=======
# Medical Annotation Tool (v0)

Streamlit-based workspace for medical abstractors to capture structured annotations from clinical text. Entries are persisted in SQLite and export to the provided gold JSON schema.

## Features
- User registration/login with salted PBKDF2 password hashing.
- Rich medical record viewer seeded with both JSON notes and the new DOCX-derived angiodysplasia case.
- Object builder that mirrors the gold schema (concept metadata, structured codes, property table with evidence offsets, inference details).
- Workflow-aware annotations: selectable statuses (Draft→Accepted), reviewer notes, inline comments, reviewer comparison view, and diff vs. system predictions.
- Evidence capture helper that calculates offsets from highlighted snippets and applies them to property rows.
- Annotation persistence per user & document; instant download, reviewer bundle export, and optional write-out to `exports/`.
- Lightweight SQLite backend plus starter unit tests for database helpers.

## Quick start
1. **Install dependencies** (preferably in a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the Streamlit app**:
   ```bash
   streamlit run app/streamlit_app.py
   ```
3. **Workflow**:
   - Register a user in the sidebar, then log in.
   - Pick a medical record from the dropdown.
   - Fill the object builder form, add properties/evidence, and click **Add object**.
   - Repeat for each object, then click **Save annotation**.
   - Download the JSON immediately or from the saved annotations section.
   - Use the sidebar export button for a bulk JSON dump of all your annotations.
   - Switch to the **History** tab to compare reviewers, leave comments, or diff against system predictions.

## Seeding new notes (DOCX ingest)

1. Drop your `.docx` file (e.g., the provided `Angiodysplas 1.docx`) into the project root.
2. Extract the paragraphs to text so they can be pasted into `data/records/sample_records.json`:
   ```bash
   python -c "from docx import Document; doc = Document('YOUR_NOTE.docx'); print('\n'.join(p.text for p in doc.paragraphs))"
   ```
3. Create a new JSON object at the top of `data/records/sample_records.json` using the emitted text for `note_body`, `med_list`, and `sections`.
4. Restart the Streamlit app—your DOCX-derived record now appears first in the queue.

The repository already includes the angiodysplasia (Heyde’s syndrome) case converted from `Angiodysplas 1.docx` following the above steps.

## Tests
Run the unit tests to smoke-test DB helpers:
```bash
pytest
```

CI is pre-wired in `.github/workflows/ci.yml` and runs these tests on every push and pull request via GitHub Actions.

## Project structure
```
app/
  db.py            # SQLite helpers for users + annotations
  schema.py        # JSON schema builders + helpers
  streamlit_app.py # Streamlit UI
  __init__.py
 data/records/     # Seed medical notes (editable JSON)
docs/architecture.md
exports/           # Placeholder for future batch exports
README.md
requirements.txt
sample gold.json
sample system prediction.json
SBS schema.csv
```

## Next steps
- Expand document ingestion (CSV uploads, EMR adapters) and auto-map sections beyond DOCX.
- Enrich validation (offset checks, ontology lookups) and extend reviewer dashboards.
- Introduce media (image/PDF/DICOM) annotation canvases.

## Deployment

While this workspace cannot be hosted directly from the coding agent’s sandbox, you can deploy it in minutes:

### Streamlit Community Cloud
1. Push this repository to GitHub.
2. Visit [share.streamlit.io](https://share.streamlit.io/) and log in with GitHub.
3. Create a new app, selecting your repo, branch (`main`), and entry point `app/streamlit_app.py`.
4. Set any required secrets/environment variables (none are required for the default SQLite setup).
5. Deploy—the platform gives you a public URL you can share with reviewers.

### GitHub-hosted CI
The included workflow `.github/workflows/ci.yml` installs dependencies and runs `pytest` on every push/PR to ensure the database layer and workflow helpers stay green. Extend it with deploy steps (e.g., Streamlit Cloud API or container publish) once you are ready to automate releases.

### Self-hosted (optional)
- Run `streamlit run app/streamlit_app.py` on a VM/container and expose port 8501 behind your preferred reverse proxy.
- For containerization, create a simple `Dockerfile` that installs `requirements.txt`, copies the repo, and sets the Streamlit entrypoint—then deploy to your platform of choice.
>>>>>>> 5d06272 (Initial commit of medical annotation tool)
