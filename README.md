# Medical Annotation Tool

Streamlit-based workspace for medical abstractors to capture structured annotations from clinical text. Entries are persisted in SQLite and exported in the provided gold JSON schema.

## Highlights

- **User accounts** with salted PBKDF2 hashing plus single-click export of everything authored by the logged-in reviewer.
- **Record navigator + queue** with keyboard shortcuts, editable note body, and an evidence helper that calculates offsets from highlighted snippets.
- **Object builder** with template-aware validation (Lab, Medication, Diagnosis) that enforces required properties, supported value types, and evidence alignment before an object is staged.
- **Enhanced vocabulary search** that ranks labels, synonyms, Mendel IDs, and codes from `data/vocab_stub.json`, showing semantic type + codes before auto-filling the concept form.
- **Workflow + collaboration**: status chips (`Draft → Accepted`), reviewer notes, inline comments, reviewer comparisons, and diffs vs. system predictions.
- **Exports**: download any single annotation, the current document’s bundle (with workflow metadata), or all annotations for the logged-in user.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Then follow the detailed [How to Use guide](docs/how_to_use.md) for abstraction, reviewing, and deployment tips.

## Workflow reference

- Read the end-to-end flow with every possible path (viewer, abstractor, reviewer) in [docs/annotation_workflow.md](docs/annotation_workflow.md).
- Architecture overview lives in [docs/architecture.md](docs/architecture.md).

## Seeding new notes (DOCX ingest)

1. Drop a `.docx` file (e.g., `Angiodysplas 1.docx`) into the project root.
2. Convert it to plain text:
   ```bash
   python -c "from docx import Document; doc = Document('YOUR_NOTE.docx'); print('\\n'.join(p.text for p in doc.paragraphs))"
   ```
3. Create or update an entry inside `data/records/sample_records.json` (`note_body`, `med_list`, optional `sections`).
4. Restart Streamlit—the new document appears first in the record queue.

## Tests

```bash
pytest
```

CI runs the same test suite via `.github/workflows/ci.yml`.

## Deployment options

- **Streamlit Community Cloud** – point the app to `app/streamlit_app.py` and deploy straight from GitHub.
- **Procfile-friendly hosts (Heroku, Render, Railway)** – the included `Procfile` runs `streamlit run app/streamlit_app.py --server.port=$PORT --server.headless=true`.
- **Container/VM** – build a tiny image that installs `requirements.txt` and launches Streamlit; mount `data/annotations.db` if you need persistence.

## Project structure

```
app/
  db.py            # SQLite helpers for users + annotations
  schema.py        # JSON schema builders + helpers
  streamlit_app.py # Streamlit UI + validation + vocab helpers
data/
  records/         # Seed medical notes (editable JSON)
  vocab_stub.json  # Controlled vocabulary entries used by the UI
docs/              # Architecture, workflow, and how-to guides
exports/           # Optional bundle output location
```

Next milestones include richer ingestion (CSV/EMR adapters), ontology-backed validation, and multimedia annotation canvases.
