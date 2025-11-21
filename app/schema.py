"""Schema helpers to mirror the gold JSON format."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List


REQUIRED_METADATA_FIELDS = [
    "patient_id",
    "source_id",
    "source_type",
    "document_date",
]


def make_document_key(patient_id: str, source_id: str) -> str:
    return f"{patient_id}::{source_id}"


def build_annotation_payload(
    note_meta: Dict[str, Any],
    annotation_meta_overrides: Dict[str, Any],
    objects: List[Dict[str, Any]],
    annotator_username: str,
) -> Dict[str, Any]:
    missing = [field for field in REQUIRED_METADATA_FIELDS if not note_meta.get(field)]
    if missing:
        raise ValueError(f"Missing required metadata fields: {', '.join(missing)}")

    annotation_meta = {
        "annotator": annotator_username,
        "annotator_role": annotation_meta_overrides.get("annotator_role", "Abstractor"),
        "annotation_date": annotation_meta_overrides.get(
            "annotation_date", dt.date.today().isoformat()
        ),
        "dataset_version": annotation_meta_overrides.get("dataset_version", "v0"),
        "key": annotation_meta_overrides.get("key", "K1"),
    }

    workflow_status = annotation_meta_overrides.get("workflow_status")
    if workflow_status:
        annotation_meta["workflow_status"] = workflow_status

    return {
        "patient_id": note_meta["patient_id"],
        "source_id": note_meta["source_id"],
        "source_type": note_meta.get("source_type", "unknown"),
        "document_date": note_meta.get("document_date", dt.date.today().isoformat()),
        "annotation_meta": annotation_meta,
        "objects": objects,
    }


def coerce_property_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "property_name": row.get("property_name", "Unnamed Property"),
        "property_value_raw": row.get("property_value_raw", ""),
        "property_value_type": row.get("property_value_type", "text"),
        "property_value_normalized": row.get("property_value_normalized"),
        "property_units": row.get("property_units"),
        "property_ucum": row.get("property_ucum"),
        "evidence": row.get("evidence", []),
        "annotator_rationale": row.get("annotator_rationale"),
    }


def build_object(
    object_index: int,
    object_type: str,
    concept: Dict[str, Any],
    properties: List[Dict[str, Any]],
    group_id: str,
) -> Dict[str, Any]:
    return {
        "object_index": object_index,
        "action": "Created",
        "object_type": object_type,
        "object_concept": concept,
        "properties": [coerce_property_row(row) for row in properties],
        "supporting_facts": concept.get("supporting_facts", []),
        "inference_type": concept.get("inference_type", "direct_extraction"),
        "group_id": group_id,
    }
