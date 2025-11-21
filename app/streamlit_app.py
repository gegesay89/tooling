from __future__ import annotations

import json
import re
import difflib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from functools import lru_cache

import pandas as pd
import streamlit as st

try:
    import sys
    CURRENT_DIR = Path(__file__).resolve().parent
    ROOT_DIR = CURRENT_DIR.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
except Exception:  # pragma: no cover - defensive path setup
    ROOT_DIR = Path(__file__).resolve().parents[1]

from app import db, schema

RECORDS_PATH = ROOT_DIR / "data" / "records" / "sample_records.json"
SYSTEM_PREDICTIONS_DIR = ROOT_DIR / "data" / "system_predictions"
VOCAB_PATH = ROOT_DIR / "data" / "vocab_stub.json"

STATUS_OPTIONS = ["Draft", "Assigned", "In Review", "Accepted"]


def status_index(value: Optional[str]) -> int:
    try:
        return STATUS_OPTIONS.index(value or STATUS_OPTIONS[0])
    except ValueError:
        return 0

OBJECT_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "Lab Finding": [
        {
            "property_name": "Result Value",
            "property_value_raw": "",
            "property_value_type": "numeric",
            "property_value_normalized": "",
            "property_units": "",
            "property_ucum": "",
            "evidence_text": "",
            "evidence_start": "",
            "evidence_end": "",
            "evidence_field": "note_body",
            "sentence_id": "",
            "annotator_rationale": "",
        },
        {
            "property_name": "Categorical Value",
            "property_value_raw": "",
            "property_value_type": "categorical",
            "property_value_normalized": "",
            "property_units": "",
            "property_ucum": "",
            "evidence_text": "",
            "evidence_start": "",
            "evidence_end": "",
            "evidence_field": "note_body",
            "sentence_id": "",
            "annotator_rationale": "",
        },
    ],
    "Medication": [
        {
            "property_name": "Dosage",
            "property_value_raw": "",
            "property_value_type": "text",
            "property_value_normalized": "",
            "property_units": "",
            "property_ucum": "",
            "evidence_text": "",
            "evidence_start": "",
            "evidence_end": "",
            "evidence_field": "med_list",
            "sentence_id": "",
            "annotator_rationale": "",
        }
    ],
    "Diagnosis": [
        {
            "property_name": "Assertion",
            "property_value_raw": "",
            "property_value_type": "text",
            "property_value_normalized": "",
            "property_units": "",
            "property_ucum": "",
            "evidence_text": "",
            "evidence_start": "",
            "evidence_end": "",
            "evidence_field": "note_body",
            "sentence_id": "",
            "annotator_rationale": "",
        }
    ],
}

DEFAULT_OBJECT_TYPES = [
    "Lab Finding",
    "Medication",
    "Diagnosis",
    "Procedure",
    "Other",
]

CHECKLIST_ITEMS = [
    {"id": "labs", "label": "Lab Findings", "object_type": "Lab Finding"},
    {"id": "meds", "label": "Medications", "object_type": "Medication"},
    {"id": "diagnosis", "label": "Diagnoses", "object_type": "Diagnosis"},
    {"id": "procedure", "label": "Procedures", "object_type": "Procedure"},
]


@lru_cache(maxsize=1)
def load_vocab_stub() -> List[Dict[str, Any]]:
    if VOCAB_PATH.exists():
        with VOCAB_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    return []


def find_vocab_suggestions(query: str) -> List[Dict[str, Any]]:
    query = query.strip().lower()
    if len(query) < 2:
        return []
    matches = []
    for entry in load_vocab_stub():
        haystack = " ".join(
            [
                entry.get("label", ""),
                entry.get("mendel_id", ""),
                entry.get("semantic_type", ""),
            ]
        ).lower()
        if query in haystack:
            matches.append(entry)
        if len(matches) >= 10:
            break
    return matches


def load_records() -> List[Dict[str, Any]]:
    if not RECORDS_PATH.exists():
        return []
    with RECORDS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _match_prediction_payload(data: Any, document_key: str) -> Optional[Dict[str, Any]]:
    if isinstance(data, list):
        for entry in data:
            if schema.make_document_key(entry.get("patient_id", ""), entry.get("source_id", "")) == document_key:
                return entry
    elif isinstance(data, dict):
        if schema.make_document_key(data.get("patient_id", ""), data.get("source_id", "")) == document_key:
            return data
    return None


def load_system_prediction(document_key: str) -> Optional[Dict[str, Any]]:
    direct_file = SYSTEM_PREDICTIONS_DIR / f"{document_key}.json"
    if direct_file.exists():
        with direct_file.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    fallback_file = ROOT_DIR / "sample system prediction.json"
    if fallback_file.exists():
        with fallback_file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return _match_prediction_payload(data, document_key)
    return None


def default_properties_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "property_name": "Result Value",
                "property_value_raw": "",
                "property_value_type": "text",
                "property_value_normalized": "",
                "property_units": "",
                "property_ucum": "",
                "evidence_text": "",
                "evidence_start": "",
                "evidence_end": "",
                "evidence_field": "note_body",
                "sentence_id": "",
                "annotator_rationale": "",
            }
        ]
    )


def template_properties_df(object_type: str) -> pd.DataFrame:
    template = OBJECT_TEMPLATES.get(object_type)
    if template:
        return pd.DataFrame(template)
    return default_properties_df().copy()


def default_codes_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "system": "LOINC",
                "code": "",
            }
        ]
    )


def slugify_label(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "field"


def find_all_occurrences(text: str, snippet: str) -> List[Tuple[int, int]]:
    if not text or not snippet:
        return []
    haystack = text.lower()
    needle = snippet.lower()
    matches: List[Tuple[int, int]] = []
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx == -1:
            break
        matches.append((idx, idx + len(snippet)))
        start = idx + 1
    return matches


def sentence_id_for_offset(text: str, offset: int) -> Optional[int]:
    if not text:
        return None
    for idx, match in enumerate(re.finditer(r"[^.!?]+[.!?]?", text), start=1):
        if match.start() <= offset < match.end():
            return idx
    return None


def build_evidence_field_options(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    fields: List[Dict[str, Any]] = []
    override_text = st.session_state.get("note_body_override")
    note_text = override_text if override_text is not None else record.get("note_body", "")
    fields.append(
        {
            "label": "Full note body",
            "field_key": "note_body",
            "text": note_text or "",
        }
    )
    med_list = record.get("med_list")
    if med_list:
        fields.append(
            {
                "label": "Medication list",
                "field_key": "med_list",
                "text": med_list,
            }
        )
    for idx, section in enumerate(record.get("sections") or []):
        label = section.get("name") or f"Section {idx + 1}"
        slug = slugify_label(label)
        fields.append(
            {
                "label": f"Section: {label}",
                "field_key": f"section_{slug}",
                "text": section.get("text", ""),
            }
        )
    return fields


def apply_vocab_to_fields(entry: Dict[str, Any]) -> None:
    st.session_state["concept_label_input"] = entry.get("label", "")
    st.session_state["concept_mendel_input"] = entry.get("mendel_id", "")
    st.session_state["concept_semantic_input"] = entry.get("semantic_type", "")
    codes = entry.get("codes", {})
    if codes:
        st.session_state["concept_codes_df"] = pd.DataFrame(
            [{"system": system, "code": value} for system, value in codes.items()]
        )


def default_checklist_state() -> Dict[str, bool]:
    return {item["id"]: False for item in CHECKLIST_ITEMS}


def ensure_session_state() -> None:
    st.session_state.setdefault("auth_user", None)
    st.session_state.setdefault("objects_buffer", [])
    st.session_state.setdefault("properties_df", default_properties_df())
    st.session_state.setdefault("concept_codes_df", default_codes_df())
    st.session_state.setdefault("checklist_state", default_checklist_state())
    st.session_state.setdefault("note_body_override", None)
    st.session_state.setdefault("note_edit_mode", False)
    st.session_state.setdefault("active_document_key", None)
    st.session_state.setdefault("record_queue", [])
    st.session_state.setdefault("record_index", 0)
    st.session_state.setdefault("queue_cursor", 0)
    st.session_state.setdefault("nav_command", "")
    st.session_state.setdefault("captured_evidence", None)
    st.session_state.setdefault("concept_label_input", "")
    st.session_state.setdefault("concept_mendel_input", "")
    st.session_state.setdefault("concept_semantic_input", "")
    st.session_state.setdefault("current_template_type", "")
    st.session_state.setdefault("selected_vocab", None)
    st.session_state.setdefault("concept_search", "")
    st.session_state.setdefault("concept_suggestion_index", 0)
    st.session_state.setdefault("capture_snippet_input", "")
    st.session_state.setdefault("capture_field_index", 0)
    st.session_state.setdefault("capture_match_index", 0)
    st.session_state.setdefault("capture_start_offset", 0)
    st.session_state.setdefault("capture_end_offset", 0)
    st.session_state.setdefault("capture_offset_signature", "")
    st.session_state.setdefault("annotation_status", STATUS_OPTIONS[0])


def sidebar_nav() -> str:
    with st.sidebar.expander("Task tabs", expanded=True):
        nav_choice = st.radio(
            "Navigation",
            ["Annotate", "History"],
            index=0,
            key="nav_choice",
            label_visibility="collapsed",
        )
    return nav_choice


def render_queue_sidebar_controls(records: List[Dict[str, Any]], labels: List[str]) -> None:
    if not records:
        return
    sync_record_queue(records)
    queue_selection = st.sidebar.multiselect(
        "Record queue",
        options=list(range(len(records))),
        default=st.session_state["record_queue"],
        format_func=lambda idx: labels[idx],
        key="record_queue_selector",
        help="Order the records you plan to work through.",
    )
    if not queue_selection:
        queue_selection = list(range(len(records)))
    queue_selection = list(dict.fromkeys(queue_selection))
    st.session_state["record_queue"] = queue_selection
    current = st.session_state.get("record_index", 0)
    if current not in queue_selection:
        current = queue_selection[0]
    st.session_state["record_index"] = current
    st.session_state["queue_cursor"] = queue_selection.index(current)

    command = st.sidebar.text_input(
        "Keyboard nav (n=next, p=prev)",
        key="nav_command",
        help="Type n or p and press Enter to move without clicking buttons.",
    )
    if command:
        apply_keyboard_nav(command)


def sync_record_queue(records: List[Dict[str, Any]]) -> None:
    total = len(records)
    if total == 0:
        st.session_state["record_queue"] = []
        st.session_state["record_index"] = 0
        st.session_state["queue_cursor"] = 0
        return
    queue = [idx for idx in st.session_state["record_queue"] if idx < total]
    if not queue:
        queue = list(range(total))
    st.session_state["record_queue"] = queue
    current_index = st.session_state.get("record_index", 0)
    if current_index not in queue:
        current_index = queue[0]
    st.session_state["record_index"] = current_index
    st.session_state["queue_cursor"] = queue.index(current_index)


def advance_record(step: int) -> None:
    queue = st.session_state.get("record_queue", [])
    if not queue:
        return
    cursor = (st.session_state.get("queue_cursor", 0) + step) % len(queue)
    st.session_state["queue_cursor"] = cursor
    st.session_state["record_index"] = queue[cursor]


def apply_keyboard_nav(command: str) -> None:
    for char in command.lower():
        if char == "n":
            advance_record(1)
        elif char == "p":
            advance_record(-1)
    st.session_state["nav_command"] = ""


def count_objects_by_type(objects: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for obj in objects:
        object_type = obj.get("object_type", "Other")
        counts[object_type] = counts.get(object_type, 0) + 1
    return counts


def render_progress_chips(
    saved_counts: Dict[str, int], in_progress_counts: Dict[str, int]
) -> None:
    cols = st.columns(len(CHECKLIST_ITEMS))
    for col, item in zip(cols, CHECKLIST_ITEMS):
        object_type = item["object_type"]
        saved = saved_counts.get(object_type, 0)
        pending = in_progress_counts.get(object_type, 0)
        delta = f"+{pending} unsaved" if pending else None
        col.metric(item["label"], saved, delta=delta)


def extract_objects_from_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    extracted: List[Dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(row["annotation_json"])
        except json.JSONDecodeError:
            continue
        extracted.extend(payload.get("objects", []))
    return extracted


def sidebar_auth() -> None:
    st.sidebar.header("User")
    auth_user = st.session_state["auth_user"]
    if auth_user:
        st.sidebar.success(f"Logged in as {auth_user['username']}")
        if st.sidebar.button("Log out"):
            st.session_state["auth_user"] = None
        saved_rows = db.list_annotations(user_id=auth_user["id"])
        if saved_rows:
            bulk_payload = [json.loads(row["annotation_json"]) for row in saved_rows]
            st.sidebar.download_button(
                label="Export my annotations (JSON)",
                data=json.dumps(bulk_payload, indent=2),
                file_name=f"{auth_user['username']}-annotations.json",
                mime="application/json",
            )
    else:
        with st.sidebar.expander("Login", expanded=True):
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", use_container_width=True):
                user = db.authenticate_user(login_username, login_password)
                if user:
                    st.session_state["auth_user"] = user
                    st.success("Logged in successfully")
                else:
                    st.error("Invalid credentials")
        with st.sidebar.expander("Register"):
            reg_username = st.text_input("New username", key="reg_username")
            reg_password = st.text_input("New password", type="password", key="reg_password")
            if st.button("Create account", use_container_width=True):
                try:
                    db.create_user(reg_username, reg_password)
                    st.success("Account created. Please log in.")
                except Exception as exc:
                    st.error(str(exc))


def reset_annotation_workspace() -> None:
    st.session_state["objects_buffer"] = []
    st.session_state["properties_df"] = default_properties_df()
    st.session_state["concept_codes_df"] = default_codes_df()


def build_property_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for _, row in df.fillna("").iterrows():
        evidence = []
        if row.get("evidence_text"):
            evidence.append(
                {
                    "text": row.get("evidence_text"),
                    "start": safe_int(row.get("evidence_start")),
                    "end": safe_int(row.get("evidence_end")),
                    "field": row.get("evidence_field") or "note_body",
                    "sentence_id": safe_int(row.get("sentence_id")),
                }
            )
        rows.append(
            {
                "property_name": row.get("property_name") or "Unnamed Property",
                "property_value_raw": row.get("property_value_raw"),
                "property_value_type": row.get("property_value_type") or "text",
                "property_value_normalized": row.get("property_value_normalized") or None,
                "property_units": row.get("property_units") or None,
                "property_ucum": row.get("property_ucum") or None,
                "evidence": evidence,
                "annotator_rationale": row.get("annotator_rationale") or None,
            }
        )
    return rows


def safe_int(value: Any) -> Any:
    try:
        return int(value)
    except (TypeError, ValueError):
        return value if value not in ("", None) else None


def render_note_info(record: Dict[str, Any]) -> None:
    st.markdown("### Note Brief Info")
    info_cols = st.columns(4)
    info_cols[0].metric("Patient", record.get("patient_id", "-"))
    info_cols[1].metric("Source", record.get("source_id", "-"))
    info_cols[2].metric("Type", record.get("source_type", "-"))
    info_cols[3].metric("Date", record.get("document_date", "-"))
    meta_cols = st.columns(3)
    meta_cols[0].write(f"**Dataset:** {record.get('dataset_version', 'v0')}")
    meta_cols[1].write(f"**Key:** {record.get('key', 'K1')}")
    meta_cols[2].write(f"**Sections:** {len(record.get('sections', []))}")


def render_note_body_panel(record: Dict[str, Any]) -> None:
    st.markdown("### Note Body")
    edit_mode = st.session_state["note_edit_mode"]
    default_text = record.get("note_body", "")
    if st.session_state["note_body_override"] is None:
        st.session_state["note_body_override"] = default_text
    text_value = st.session_state["note_body_override"]
    if edit_mode:
        new_text = st.text_area("Edit clinical note", value=text_value, height=350, key="note_editor")
        st.session_state["note_body_override"] = new_text
    else:
        st.write(text_value or "No note body available")
    edit_col, reset_col = st.columns(2)
    if edit_col.button("Edit" if not edit_mode else "Stop editing"):
        st.session_state["note_edit_mode"] = not edit_mode
    if reset_col.button("Reset text"):
        st.session_state["note_body_override"] = default_text
    sections = record.get("sections")
    if sections:
        st.markdown("### Sections")
        for section in sections:
            with st.expander(section.get("name", "Section"), expanded=False):
                st.write(section.get("text", ""))

    render_evidence_capture_helper(record)


def render_evidence_capture_helper(record: Dict[str, Any]) -> None:
    fields = build_evidence_field_options(record)
    if not fields:
        return

    with st.expander("Evidence capture helper", expanded=False):
        st.caption("Paste highlighted note text to auto-calculate offsets, adjust manually, then capture.")
        st.session_state["capture_field_index"] = min(
            st.session_state.get("capture_field_index", 0), len(fields) - 1
        )
        field_index = st.selectbox(
            "Field",
            options=list(range(len(fields))),
            format_func=lambda idx: fields[idx]["label"],
            index=st.session_state["capture_field_index"],
            key="capture_field_index",
        )
        field_meta = fields[field_index]
        field_text = field_meta.get("text", "") or ""

        snippet_value = st.text_area(
            "Paste selected text (optional)",
            key="capture_snippet_input",
            height=120,
        ).strip()

        matches = find_all_occurrences(field_text, snippet_value) if snippet_value else []
        if snippet_value and not matches:
            st.warning("Snippet not found in this field. Adjust the text or choose a different field.")

        match_index: Optional[int] = None
        if matches:
            st.session_state["capture_match_index"] = min(
                st.session_state.get("capture_match_index", 0), len(matches) - 1
            )
            match_index = st.selectbox(
                "Matching spans",
                options=list(range(len(matches))),
                format_func=lambda idx: f"{matches[idx][0]}–{matches[idx][1]}",
                index=st.session_state["capture_match_index"],
                key="capture_match_index",
            )
        else:
            st.session_state["capture_match_index"] = 0

        signature_bits = [str(field_index), snippet_value]
        if match_index is not None:
            signature_bits.append(str(match_index))
        signature = "|".join(signature_bits)
        previous_signature = st.session_state.get("capture_offset_signature", "")
        if matches and match_index is not None and signature != previous_signature:
            start_guess, end_guess = matches[match_index]
            st.session_state["capture_start_offset"] = start_guess
            st.session_state["capture_end_offset"] = end_guess
            st.session_state["capture_offset_signature"] = signature
        elif not matches and signature != previous_signature:
            st.session_state["capture_start_offset"] = 0
            st.session_state["capture_end_offset"] = min(len(field_text), max(1, len(field_text)))
            st.session_state["capture_offset_signature"] = signature

        max_value = len(field_text)
        start_key = "capture_start_offset"
        end_key = "capture_end_offset"
        if max_value:
            st.session_state[start_key] = min(st.session_state.get(start_key, 0), max_value - 1)
        else:
            st.session_state[start_key] = 0
        st.session_state[end_key] = min(
            max(st.session_state.get(end_key, 1), st.session_state[start_key] + (1 if max_value else 0)),
            max_value,
        )

        start_offset = st.number_input(
            "Start offset",
            min_value=0,
            max_value=max_value - 1 if max_value else 0,
            key=start_key,
        )
        end_offset = st.number_input(
            "End offset",
            min_value=0,
            max_value=max_value,
            key=end_key,
        )

        preview = field_text[start_offset:end_offset]
        st.text_area("Preview", value=preview, height=120, disabled=True)

        capture_col, clear_col = st.columns([0.6, 0.4])
        if capture_col.button("Capture selection", use_container_width=True, key="capture_selection_button"):
            if end_offset <= start_offset:
                st.error("End offset must be greater than start offset.")
            elif not preview.strip():
                st.error("Selected span is empty.")
            else:
                st.session_state["captured_evidence"] = {
                    "text": preview,
                    "start": start_offset,
                    "end": end_offset,
                    "field": field_meta["field_key"],
                    "sentence_id": sentence_id_for_offset(field_text, start_offset),
                }
                st.success("Evidence captured. Use 'Apply captured evidence' in the object builder.")

        if clear_col.button("Clear selection", use_container_width=True, key="clear_capture_button"):
            st.session_state["captured_evidence"] = None
            st.session_state["capture_snippet_input"] = ""
            st.session_state["capture_offset_signature"] = ""
            st.session_state["capture_match_index"] = 0
            st.session_state["capture_start_offset"] = 0
            st.session_state["capture_end_offset"] = 0


def render_checklist_panel(
    saved_counts: Dict[str, int], in_progress_counts: Dict[str, int]
) -> List[str]:
    st.markdown("#### Abstraction Checklist")
    render_progress_chips(saved_counts, in_progress_counts)
    st.caption("Mark the families you plan to abstract; selected items drive the object form.")
    selected_types: List[str] = []
    for item in CHECKLIST_ITEMS:
        key = f"checklist_{item['id']}"
        if key not in st.session_state:
            st.session_state[key] = st.session_state["checklist_state"].get(item["id"], False)
        checked = st.checkbox(item["label"], value=st.session_state[key], key=key)
        st.session_state["checklist_state"][item["id"]] = checked
        if checked:
            selected_types.append(item["object_type"])
    return selected_types


def resolve_object_type_options(selected_types: List[str]) -> List[str]:
    if not selected_types:
        return DEFAULT_OBJECT_TYPES
    ordered: List[str] = []
    for opt in selected_types + DEFAULT_OBJECT_TYPES:
        if opt not in ordered:
            ordered.append(opt)
    return ordered


def codes_df_to_dict(df: pd.DataFrame) -> Dict[str, str]:
    codes: Dict[str, str] = {}
    for _, row in df.fillna("").iterrows():
        system = row.get("system", "").strip()
        code = row.get("code", "").strip()
        if system and code:
            codes[system] = code
    return codes


def render_saved_annotations(
    rows: List[Dict[str, Any]],
    document_key: str,
    expanded: bool,
    current_user: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    st.markdown("### My Saved Annotations")
    if not rows:
        st.caption("No local annotations saved yet. Add an object and click Save to persist.")
        return None

    latest_payload: Optional[Dict[str, Any]] = None
    for idx, row in enumerate(rows):
        header_status = row.get("status", "Draft")
        owner = row.get("owner_username", "")
        updated = row.get("updated_at", "")[:19]
        header = f"Annotation #{row['id']} · {header_status} · {updated}"
        with st.expander(header, expanded=(expanded and idx == 0)):
            payload = json.loads(row["annotation_json"])
            if latest_payload is None:
                latest_payload = payload

            meta_cols = st.columns(3)
            meta_cols[0].write(f"**Owner:** {owner or row.get('user_id')}")
            meta_cols[1].write(f"**Status:** {header_status}")
            meta_cols[2].write(f"**Objects:** {len(payload.get('objects', []))}")

            if current_user:
                workflow_cols = st.columns([0.4, 0.6])
                status_value = workflow_cols[0].selectbox(
                    "Update status",
                    STATUS_OPTIONS,
                    index=status_index(row.get("status")),
                    key=f"status_select_{row['id']}",
                )
                reviewer_key = f"reviewer_note_{row['id']}"
                if reviewer_key not in st.session_state:
                    st.session_state[reviewer_key] = row.get("reviewer_notes", "") or ""
                reviewer_notes = workflow_cols[1].text_area(
                    "Reviewer notes",
                    key=reviewer_key,
                    height=80,
                )
                if st.button("Apply workflow update", key=f"workflow_btn_{row['id']}"):
                    db.update_annotation_status(
                        row["id"],
                        status_value,
                        reviewer_id=current_user["id"],
                        reviewer_notes=reviewer_notes,
                    )
                    st.success("Workflow updated")
                    st.experimental_rerun()
            else:
                st.caption("Log in to update workflow status or add comments.")

            st.json(payload)
            st.download_button(
                label=f"Download #{row['id']}",
                data=row["annotation_json"],
                file_name=f"{document_key}-annotation-{row['id']}.json",
                mime="application/json",
                key=f"download_saved_{row['id']}",
            )

            render_comments_block(row["id"], current_user)

    return latest_payload


def render_comments_block(annotation_id: int, current_user: Optional[Dict[str, Any]]) -> None:
    st.markdown("##### Comments")
    comments = db.list_comments(annotation_id)
    if comments:
        for item in comments:
            st.write(
                f"**{item['username']}** ({item['created_at']}): {item['message']}"
            )
    else:
        st.caption("No comments yet on this annotation.")

    if not current_user:
        st.caption("Log in to leave a comment.")
        return

    comment_key = f"comment_input_{annotation_id}"
    new_comment = st.text_area(
        "Add comment",
        key=comment_key,
        height=80,
    )
    if st.button("Post comment", key=f"comment_btn_{annotation_id}"):
        try:
            db.create_comment(annotation_id, current_user["id"], new_comment)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.success("Comment added")
            st.session_state[comment_key] = ""
            st.experimental_rerun()


def build_annotation_label(row: Dict[str, Any]) -> str:
    owner = row.get("owner_username") or f"user_{row.get('user_id')}"
    status_value = row.get("status", "Draft")
    updated = (row.get("updated_at") or "")[:19]
    return f"#{row['id']} · {owner} · {status_value} · {updated}"


def render_reviewer_compare(rows: List[Dict[str, Any]]) -> None:
    st.markdown("### Reviewer comparison")
    if len(rows) < 2:
        st.caption("At least two saved annotations are required for comparison.")
        return

    option_ids = [row["id"] for row in rows]
    label_map = {row["id"]: build_annotation_label(row) for row in rows}
    primary_id = st.selectbox(
        "Primary annotation",
        options=option_ids,
        format_func=lambda rid: label_map[rid],
        key="review_primary",
    )
    secondary_candidates = [rid for rid in option_ids if rid != primary_id] or option_ids
    secondary_id = st.selectbox(
        "Comparison annotation",
        options=secondary_candidates,
        format_func=lambda rid: label_map[rid],
        key="review_secondary",
    )

    if primary_id == secondary_id:
        st.warning("Select two different annotations to compare.")
        return

    primary_row = next(row for row in rows if row["id"] == primary_id)
    secondary_row = next(row for row in rows if row["id"] == secondary_id)
    primary_payload = json.loads(primary_row["annotation_json"])
    secondary_payload = json.loads(secondary_row["annotation_json"])

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(label_map[primary_id])
        st.json(primary_payload)
    with col2:
        st.subheader(label_map[secondary_id])
        st.json(secondary_payload)

    diff = "\n".join(
        difflib.unified_diff(
            json.dumps(primary_payload, indent=2, ensure_ascii=False).splitlines(),
            json.dumps(secondary_payload, indent=2, ensure_ascii=False).splitlines(),
            fromfile=label_map[primary_id],
            tofile=label_map[secondary_id],
        )
    )
    st.markdown("#### Object diff")
    if diff:
        st.code(diff, language="diff")
    else:
        st.success("No differences between the selected annotations.")


def render_prediction_diff(document_key: str, latest_payload: Optional[Dict[str, Any]]) -> None:
    st.markdown("### System prediction diff")
    if not latest_payload:
        st.caption("Save an annotation to enable diffing against system predictions.")
        return
    system_prediction = load_system_prediction(document_key)
    if not system_prediction:
        st.caption("No system prediction file found for this document.")
        return

    user_text = json.dumps(latest_payload, indent=2, ensure_ascii=False)
    sys_text = json.dumps(system_prediction, indent=2, ensure_ascii=False)
    diff = "\n".join(
        difflib.unified_diff(
            sys_text.splitlines(),
            user_text.splitlines(),
            fromfile="system_prediction",
            tofile="user_annotation",
        )
    )
    if diff:
        st.code(diff, language="diff")
    else:
        st.success("Your annotation matches the system prediction exactly.")


def render_document_exports(document_key: str, rows: List[Dict[str, Any]]) -> None:
    st.markdown("### Batch export")
    if not rows:
        st.caption("No annotations available to export yet.")
        return

    bundle: List[Dict[str, Any]] = []
    for row in rows:
        payload = json.loads(row["annotation_json"])
        payload.setdefault("_workflow", {})
        payload["_workflow"].update(
            {
                "annotation_id": row["id"],
                "owner": row.get("owner_username"),
                "status": row.get("status", "Draft"),
                "reviewer_id": row.get("reviewer_id"),
                "reviewer_notes": row.get("reviewer_notes"),
                "updated_at": row.get("updated_at"),
            }
        )
        bundle.append(payload)

    bundle_json = json.dumps(bundle, indent=2, ensure_ascii=False)
    st.download_button(
        "Download bundle (JSON)",
        data=bundle_json,
        file_name=f"{document_key}-bundle.json",
        mime="application/json",
        use_container_width=True,
    )

    exports_dir = ROOT_DIR / "exports"
    exports_dir.mkdir(exist_ok=True)
    export_path = exports_dir / f"{document_key}-bundle.json"
    if st.button("Write bundle to exports/", use_container_width=True):
        export_path.write_text(bundle_json, encoding="utf-8")
        st.success(f"Wrote {export_path.relative_to(ROOT_DIR)}")


def render_annotation_workspace(record: Dict[str, Any], object_type_options: List[str]) -> None:
    st.markdown("#### Object Builder")
    note_meta = {
        "patient_id": record.get("patient_id"),
        "source_id": record.get("source_id"),
        "source_type": record.get("source_type"),
        "document_date": record.get("document_date"),
    }
    col1, col2 = st.columns(2)
    dataset_version = col1.text_input("Dataset version", value=record.get("dataset_version", "v0"))
    key_value = col2.text_input("Annotation key", value=record.get("key", "K1"))
    annotator_role = col1.selectbox("Annotator role", ["Abstractor", "Gold", "Test"], index=0)
    annotation_date = col2.date_input("Annotation date")
    annotation_status = st.selectbox(
        "Workflow status",
        STATUS_OPTIONS,
        index=status_index(st.session_state.get("annotation_status")),
    )
    st.session_state["annotation_status"] = annotation_status

    with st.form("object_form", clear_on_submit=False):
        object_type = st.selectbox("Object type", object_type_options, index=0)
        if st.session_state["current_template_type"] != object_type:
            st.session_state["properties_df"] = template_properties_df(object_type)
            st.session_state["current_template_type"] = object_type

        concept_search = st.text_input(
            "Concept search (stub vocab)",
            key="concept_search",
            help="Type at least 2 characters to see suggestions",
        )
        suggestions: List[Dict[str, Any]] = find_vocab_suggestions(concept_search)
        apply_vocab_clicked = False
        if suggestions:
            suggestion_idx = st.selectbox(
                "Suggestions",
                options=list(range(len(suggestions))),
                format_func=lambda idx: f"{suggestions[idx]['label']} ({suggestions[idx].get('mendel_id','')})",
                key="concept_suggestion_index",
            )
            apply_vocab_clicked = st.form_submit_button("Apply suggestion", use_container_width=True)

        concept_label = st.text_input("Concept label", key="concept_label_input")
        concept_mendel = st.text_input("Mendel ID", key="concept_mendel_input")
        concept_semantic = st.text_input("Semantic type", key="concept_semantic_input")
        st.caption("Codes")
        codes_editor = st.data_editor(
            st.session_state["concept_codes_df"],
            num_rows="dynamic",
            use_container_width=True,
            key="concept_codes_editor",
        )
        st.session_state["concept_codes_df"] = pd.DataFrame(codes_editor)

        properties_df = st.data_editor(
            st.session_state["properties_df"],
            num_rows="dynamic",
            use_container_width=True,
            key="properties_editor",
        )
        st.session_state["properties_df"] = pd.DataFrame(properties_df)
        captured = st.session_state.get("captured_evidence")
        if captured:
            st.info(
                f"Captured evidence: '{captured['text']}' ({captured['start']}-{captured['end']}) in {captured['field']}"
            )
        capture_rows = list(range(len(properties_df))) if len(properties_df) > 0 else [0]
        target_row = st.number_input(
            "Row to apply captured evidence",
            min_value=0,
            max_value=max(capture_rows),
            value=0,
            step=1,
            key="capture_row_index",
        )
        apply_capture_clicked = st.form_submit_button("Apply captured evidence", use_container_width=True)

        add_object_clicked = st.form_submit_button("Add object", use_container_width=True)

        if apply_vocab_clicked:
            apply_vocab_to_fields(suggestions[suggestion_idx])
        elif apply_capture_clicked:
            if captured:
                df = st.session_state["properties_df"].copy()
                df.loc[target_row, "evidence_text"] = captured["text"]
                df.loc[target_row, "evidence_start"] = captured["start"]
                df.loc[target_row, "evidence_end"] = captured["end"]
                df.loc[target_row, "evidence_field"] = captured["field"]
                df.loc[target_row, "sentence_id"] = captured.get("sentence_id", "")
                st.session_state["properties_df"] = df
                st.success("Evidence applied to property row")
            else:
                st.warning("Capture evidence from the note first")
        elif add_object_clicked:
            concept: Dict[str, Any] = {
                "label": concept_label,
                "mendel_id": concept_mendel,
                "semantic_type": concept_semantic,
            }
            if not concept_label.strip():
                st.error("Concept label is required")
                st.stop()
            codes_dict = codes_df_to_dict(st.session_state["concept_codes_df"])
            if codes_dict:
                concept["codes"] = codes_dict
            properties = build_property_rows(properties_df)
            if not any(prop.get("property_value_raw") for prop in properties):
                st.error("Provide at least one property value before adding the object.")
                st.stop()
            object_index = len(st.session_state["objects_buffer"]) + 1
            group_id = f"{record.get('patient_id')}::{record.get('source_id')}::obj{object_index}"
            st.session_state["objects_buffer"].append(
                schema.build_object(object_index, object_type, concept, properties, group_id)
            )
            st.session_state["properties_df"] = pd.DataFrame(properties_df)
            st.session_state["concept_codes_df"] = default_codes_df()
            st.session_state["captured_evidence"] = None
            st.success(f"Added object #{object_index}")

    if not st.session_state["objects_buffer"]:
        st.info("Add at least one object to save the annotation.")
    else:
        for idx, obj in enumerate(st.session_state["objects_buffer"], start=1):
            with st.expander(f"Object #{idx}: {obj['object_type']} :: {obj['object_concept'].get('label', '')}"):
                st.json(obj)
                if st.button(f"Remove object #{idx}", key=f"remove_{idx}"):
                    st.session_state["objects_buffer"].pop(idx - 1)
                    st.experimental_rerun()

    if st.button("Reset workspace"):
        reset_annotation_workspace()

    if st.button("Save annotation", type="primary", use_container_width=True):
        if not st.session_state["auth_user"]:
            st.error("Please log in before saving.")
            return
        if not st.session_state["objects_buffer"]:
            st.error("Add at least one object before saving.")
            return
        payload = schema.build_annotation_payload(
            note_meta,
            {
                "dataset_version": dataset_version,
                "key": key_value,
                "annotator_role": annotator_role,
                "annotation_date": annotation_date.isoformat(),
                "workflow_status": annotation_status,
            },
            st.session_state["objects_buffer"],
            st.session_state["auth_user"]["username"],
        )
        document_key = schema.make_document_key(record["patient_id"], record["source_id"])
        db.upsert_annotation(
            st.session_state["auth_user"]["id"],
            document_key,
            json.dumps(payload, ensure_ascii=False, indent=2),
            status=annotation_status,
        )
        st.success("Annotation saved to database.")

        st.download_button(
            label="Download JSON",
            data=json.dumps(payload, indent=2),
            file_name=f"{document_key}.json",
            mime="application/json",
            key=f"download_{document_key}",
        )

        st.session_state["properties_df"] = pd.DataFrame(properties_df)


def render_document_viewer(records: List[Dict[str, Any]], nav_choice: str) -> None:
    st.subheader("Medical Records")
    if not records:
        st.warning("No records found. Add files to data/records.")
        return
    record_labels = [f"{item['patient_id']} :: {item['source_id']}" for item in records]
    render_queue_sidebar_controls(records, record_labels)
    current_index = min(st.session_state.get("record_index", 0), len(records) - 1)
    selected_index = st.selectbox(
        "Select record",
        options=list(range(len(records))),
        index=current_index,
        format_func=lambda idx: record_labels[idx],
    )
    if selected_index != st.session_state.get("record_index"):
        st.session_state["record_index"] = selected_index
        queue = st.session_state.get("record_queue", [])
        if selected_index in queue:
            st.session_state["queue_cursor"] = queue.index(selected_index)
        else:
            queue.append(selected_index)
            queue = list(dict.fromkeys(queue))
            st.session_state["record_queue"] = queue
            st.session_state["queue_cursor"] = queue.index(selected_index)

    nav_prev, nav_next = st.columns([0.5, 0.5])
    if nav_prev.button("← Prev (p)", use_container_width=True):
        advance_record(-1)
        selected_index = st.session_state["record_index"]
    if nav_next.button("Next (n) →", use_container_width=True):
        advance_record(1)
        selected_index = st.session_state["record_index"]

    record = records[selected_index]
    document_key = schema.make_document_key(record["patient_id"], record["source_id"])

    all_rows: List[Dict[str, Any]] = db.list_annotations(document_key=document_key)
    auth_user = st.session_state["auth_user"]
    saved_rows: List[Dict[str, Any]] = []
    if auth_user:
        saved_rows = [row for row in all_rows if row["user_id"] == auth_user["id"]]
    saved_objects = extract_objects_from_rows(saved_rows)
    session_objects = st.session_state["objects_buffer"] or []
    saved_counts = count_objects_by_type(saved_objects)
    session_counts = count_objects_by_type(session_objects)

    if st.session_state["active_document_key"] != document_key:
        st.session_state["active_document_key"] = document_key
        st.session_state["note_body_override"] = record.get("note_body", "")
        st.session_state["note_edit_mode"] = False
        st.session_state["annotation_status"] = STATUS_OPTIONS[0]
        st.session_state["captured_evidence"] = None
        st.session_state["capture_snippet_input"] = ""
        st.session_state["capture_start_offset"] = 0
        st.session_state["capture_end_offset"] = 0
        st.session_state["capture_offset_signature"] = ""
        st.session_state["capture_match_index"] = 0
        st.session_state["capture_field_index"] = 0
        reset_annotation_workspace()
        for item in CHECKLIST_ITEMS:
            st.session_state["checklist_state"][item["id"]] = False
            st.session_state.pop(f"checklist_{item['id']}", None)

    render_note_info(record)
    note_col, abstraction_col = st.columns([1.15, 0.85])
    with note_col:
        render_note_body_panel(record)
    with abstraction_col:
        selected_types = render_checklist_panel(saved_counts, session_counts)
        options = resolve_object_type_options(selected_types)
        render_annotation_workspace(record, options)

    latest_payload = render_saved_annotations(
        saved_rows,
        document_key,
        expanded=(nav_choice == "History"),
        current_user=auth_user,
    )
    render_prediction_diff(document_key, latest_payload)
    render_reviewer_compare(all_rows)
    render_document_exports(document_key, all_rows)


def main() -> None:
    st.set_page_config(page_title="Medical Annotation Tool", layout="wide")
    st.title("Medical Record Annotation v0")
    ensure_session_state()
    db.init_db()
    nav_choice = sidebar_nav()
    sidebar_auth()

    if not st.session_state["auth_user"]:
        st.info("Log in or register to start annotating.")
    records = load_records()
    render_document_viewer(records, nav_choice)


if __name__ == "__main__":
    main()
