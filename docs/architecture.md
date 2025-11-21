# Streamlit Annotation Tool v0 Architecture

## Goals
- Capture medical text annotations aligned to provided gold JSON schema.
- Support user accounts (self-serve registration + login) to track authorship.
- Persist annotations in a lightweight database and allow JSON export per record.
- Provide an ergonomic Streamlit UI for browsing records, reading text, and entering annotations.

## High-level Components
1. **Streamlit Frontend (`app/streamlit_app.py`)**
   - Session-managed login/registration form with password hashing.
   - Document navigator listing available medical notes (text-only in v0).
   - Annotation workspace showing selected note text plus structured forms for:
     - Document metadata (patient/source ids, dates, key, dataset version).
     - Objects list (object type, concept metadata, properties table, evidence snippets).
   - Controls to save draft/final annotations and export JSON for a single record or batched selection.

2. **Data/Content Layer (`data/records/*.json`)**
   - Seed file describing available notes with patient/source metadata + raw text fields.
   - Loader utility to make these records selectable inside Streamlit.

3. **Persistence Layer (`app/db.py`)**
   - SQLite database (`data/annotations.db`).
   - Tables:
     - `users(id, username, password_hash, created_at)`.
     - `documents(id, patient_id, source_id, source_type, document_date, text, created_at)` (optional seeding for quick demos).
     - `annotations(id, user_id, document_id, annotation_json, created_at, updated_at)`.
   - Helper functions: init_db, create_user, authenticate_user, list_documents, save_annotation, list_annotations, export_annotation.

4. **Schema Utilities (`app/schema.py`)**
   - Dataclasses / helper functions to build JSON structures that mirror gold schema (annotation-level metadata + objects).
   - Validation (basic) to ensure mandatory fields before persistence/export.

5. **Tests (`tests/test_db.py`)**
   - Cover DB init, user creation, annotation CRUD, JSON structure generation.

## Data Flow
1. User registers/logs in -> session stores `user_id`.
2. User selects document -> note text + metadata shown.
3. User enters annotation data -> form captured into structured Python dict.
4. On save, dict persisted as JSON in SQLite (`annotations.annotation_json`).
5. Export button dumps JSON(s) via Streamlit download or writes to `exports/`.

## Future Enhancements
- Image annotation support with drag/drop or DICOM viewer.
- Role-based permissions and audit logging.
- Collaborative review workflow (Gold vs System predictions) using SBS schema.
- Advanced validation (e.g., ensuring evidence offsets match note text).
