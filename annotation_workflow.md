# Annotation Workflow

This document explains every path available to abstractors and reviewers inside the Streamlit medical annotation tool. It is organized as a sequence diagram in prose so you can quickly identify what happens in each state.

## Roles and prerequisites

- **Viewer** – anyone who opens the app. They can browse notes but cannot save without logging in.
- **Abstractor** – a logged-in user creating or updating annotations.
- **Reviewer** – a logged-in user comparing submissions, updating workflow status, and leaving comments.
- **Data sources** – clinical note JSON in `data/records/`, optional DOCX-derived notes, and the controlled vocabulary stub in `data/vocab_stub.json`.

Before annotating, make sure the database is initialized (Streamlit does this automatically) and at least one record exists in `data/records/`.

## Happy-path abstraction flow

1. **Authenticate**
   - If not logged in, only note browsing is enabled.
   - `Login` sidebar form authenticates existing accounts; `Register` creates a new salted+hashed credential pair.

2. **Plan the queue**
   - Use the sidebar queue multiselect to order records.
   - Keyboard shortcuts `n` (next) / `p` (previous) work anywhere the focus is on the navigation input.

3. **Read the record**
   - Main column displays metadata, editable note body, sections, and the evidence helper.
   - Optional branch: toggle **Edit** to clean up OCR, then **Reset** to revert.

4. **Capture evidence**
   - Path A (auto): paste highlighted text → the helper finds offsets → choose the correct field/occurrence → capture.
   - Path B (manual): skip pasting and type offsets directly, then capture; offsets are validated against the selected field length.
   - Clearing the helper resets snippet, offsets, and selection state.

5. **Select checklist + object template**
   - Tick families (Lab, Medication, Diagnosis, Procedure) in the checklist.
   - Object type dropdown is pre-populated with the checked families to reduce scroll.
   - Switching the object type swaps in the corresponding property template rows.

6. **Apply vocabulary (optional but recommended)**
   - Type a label, synonym, Mendel ID, or code.
   - Enhanced lookup scores matches on labels, synonyms, and codes, giving preference to the chosen object type.
   - Selecting a suggestion displays semantic type, preferred object type, synonyms, and codes before you click **Apply**.

7. **Fill required fields**
   - Template validation enforces object-specific requirements:
     - *Lab Finding* → `Result Value` (numeric) with captured evidence.
     - *Medication* → `Dosage` with evidence.
     - *Diagnosis* → `Assertion` with evidence.
   - All rows must use supported value types (`text`, `numeric`, `categorical`, `boolean`, `date`, `json`).
   - Evidence offsets are checked against the source field and must reproduce the highlighted substring exactly.

8. **Add object**
   - If validation passes, the object is staged in the session buffer.
   - You may expand/inspect each staged object or remove it before saving.

9. **Save annotation**
   - Requires login **and** at least one staged object.
   - Persists to SQLite, tied to the current `(patient_id, source_id)` document key.
   - Streamlit immediately exposes a one-click JSON download of the saved payload.

10. **Advance to the next record** or stay to continue editing; the record queue cursor moves accordingly.

## Alternative paths and edge cases

| Path | Trigger | Outcome |
|------|---------|---------|
| Not logged in but clicks **Save annotation** | `auth_user` is `None` | Blocking error urging the user to log in. |
| Template violations | Missing required property, invalid value type, or mismatched evidence substring | Errors are rendered inline and submission halts until fixed. |
| Evidence with non-integer offsets | Validation catches the issue and prompts for integers. |
| Queue navigation past the end | Wraps to the beginning (circular queue). |
| Reset workspace | Clears staged objects, property table, and codes dataframe for a clean start. |
| Switching documents | Resets workspace, checklist, captured evidence, and scroll state to avoid cross-record leakage. |

## Workflow statuses and reviewer actions

| Status | Intended use | Allowed transitions |
|--------|---------------|---------------------|
| `Draft` | Initial save during abstraction. | `Assigned`, `In Review`, `Accepted`. |
| `Assigned` | Work queued for review. | `In Review`, `Accepted`. |
| `In Review` | Reviewer actively verifying content. | `Accepted` or back to `Assigned`. |
| `Accepted` | Finalized annotation (read-only expectation). | N/A (can downgrade manually if needed). |

Reviewers operate from the **My Saved Annotations** accordion within the selected record:

1. Expand an annotation to inspect its JSON payload.
2. Adjust the status dropdown and leave reviewer notes.
3. Click **Apply workflow update** to persist the new status, reviewer ID, and notes.
4. Optionally add threaded comments for back-and-forth with abstractors.

## History, comparison, and exports

- **History tab**: toggles the saved annotations accordion open by default for faster QA.
- **Reviewer comparison**: select any two saved annotations to view the raw payloads and a unified diff.
- **System prediction diff**: once at least one annotation is saved, compare it against `data/system_predictions/<document_key>.json` or the fallback sample file.
- **Batch export**: download a bundle that includes workflow metadata for every annotation tied to the current document; also write it to `exports/` if you need a local artifact.

This workflow, along with the validations and enhanced vocab function, guarantees that every path—whether abstractor, reviewer, or read-only viewer—has a defined outcome and no silent failures.
