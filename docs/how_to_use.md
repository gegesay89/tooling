# How to Use the Medical Annotation Tool

This guide walks through setup, daily abstraction tasks, review tooling, and deployment options for the Streamlit-based medical annotation workspace.

## 1. Prerequisites

- Python 3.10+ with pip available.
- macOS, Linux, or Windows shell access.
- Optional: GitHub account for Streamlit Community Cloud deployments.

## 2. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Skip the virtual environment if you already manage packages globally.

## 3. Launch the app locally

```bash
streamlit run app/streamlit_app.py
```

The UI opens at `http://localhost:8501`. The first launch creates `data/annotations.db` automatically.

## 4. Load or extend source data

1. Edit `data/records/sample_records.json` to add/remove clinical documents.
2. To ingest a DOCX file, convert it to plain text and paste into the JSON record:
   ```bash
   python -c "from docx import Document; doc = Document('path/to/note.docx'); print('\n'.join(p.text for p in doc.paragraphs))"
   ```
3. (Optional) Update `data/vocab_stub.json` with institution-specific labels, synonyms, and codes. Each entry supports:
   ```json
   {
     "label": "Complete Blood Count",
     "mendel_id": "CBC-001",
     "semantic_type": "LabTest",
     "preferred_object_type": "Lab Finding",
     "synonyms": ["CBC"],
     "codes": {"LOINC": "718-7"},
     "description": "Panel measuring ..."
   }
   ```

## 5. Daily abstraction workflow

1. **Log in / register** via the sidebar. Saved annotations are scoped to your user account.
2. **Queue documents** using the multiselect (order anything you want to process). Use `n` / `p` keyboard navigation to advance.
3. **Read & prep the note**
   - Review the metadata tiles.
   - Toggle *Edit* if you need to tidy pasted text (Streamlit keeps an override per record).
4. **Capture evidence**
   - Paste the highlighted snippet or enter offsets manually.
   - Choose the appropriate field (note body, med list, or a specific section) and hit *Capture selection*.
5. **Configure the checklist & template**
   - Tick the abstraction checklist to prioritize object families.
   - Selecting an object type loads its template rows automatically.
6. **Vocab lookup**
   - Type any label, synonym, Mendel ID, or code string.
   - Choose from the ranked suggestions (semantic type, preferred object type, codes, and synonyms display inline) and click *Apply suggestion*.
7. **Fill required fields**
   - Each object type enforces required rows:
     - Lab Finding → `Result Value` (numeric, with evidence).
     - Medication → `Dosage` (with evidence).
     - Diagnosis → `Assertion` (with evidence).
   - Evidence offsets must match the substring of the chosen field; validation catches mismatches, unsupported value types, or missing values before an object is added.
8. **Add objects** and repeat as needed. You can expand any staged object to inspect JSON or remove it.
9. **Save annotation** when satisfied. The app persists the payload, provides a download button, and keeps workflow status (`Draft`, `Assigned`, `In Review`, `Accepted`).

## 6. Reviewer vantage points

- **My Saved Annotations** accordion – update status, leave reviewer notes, or delete unwanted drafts.
- **Comments** – threaded discussions per annotation (requires login).
- **History tab** – opens saved annotations by default for quicker QA cycles.
- **Reviewer comparison** – pick any two annotations to see their JSON plus a unified diff.
- **System prediction diff** – compares the latest saved payload with baseline predictions stored in `data/system_predictions/` or `sample system prediction.json`.

## 7. Export options

- **Single-user export** – sidebar download of all annotations authored by the logged-in user.
- **Per-document bundle** – download or write a JSON bundle containing workflow metadata for every annotation tied to the current record (see `exports/`).

## 8. Deployment

### Streamlit Community Cloud
1. Push the repo to GitHub.
2. In [share.streamlit.io](https://share.streamlit.io/), create a new app targeting `app/streamlit_app.py`.
3. No secrets are required for the default SQLite setup. Deploy and share the generated URL.

### Heroku / Render / Railway
- The included `Procfile` runs `streamlit run app/streamlit_app.py --server.port=$PORT --server.headless=true` so it works out-of-the-box on any platform honoring Procfiles.
- Add a persistent volume for `data/annotations.db` if you need durable storage.

### Container / VM
```bash
cat <<'EOF' > Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.headless=true"]
EOF
```

Build + run locally or push to your orchestrator of choice.

## 9. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Missing required metadata` when saving | Ensure each record in `data/records/` includes `patient_id`, `source_id`, `source_type`, and `document_date`. |
| `Evidence text does not match substring` | Re-open the evidence helper, verify offsets, and recapture so they align with the chosen field. |
| No vocab suggestions | Confirm `data/vocab_stub.json` exists and your query is at least two characters long. |
| Tests failing | Run `pytest` and ensure you executed commands from the repo root (the test suite targets the SQLite helper functions). |

You're now set up to annotate, review, and ship structured medical data with confidence.
