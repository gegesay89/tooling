import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import db


def setup_temp_db(tmp_path: Path) -> None:
    db.DATA_DIR = tmp_path
    db.DB_PATH = tmp_path / "annotations.db"
    db.init_db()


def test_create_and_authenticate_user(tmp_path):
    setup_temp_db(tmp_path)
    db.create_user("alice", "secret123")
    user = db.authenticate_user("alice", "secret123")
    assert user is not None
    assert user["username"] == "alice"
    assert db.authenticate_user("alice", "wrong") is None


def test_upsert_and_list_annotations(tmp_path):
    setup_temp_db(tmp_path)
    db.create_user("bob", "pass456")
    user = db.authenticate_user("bob", "pass456")
    payload = {
        "patient_id": "patient_001",
        "source_id": "note_001",
        "source_type": "oncology",
        "document_date": "2025-01-01",
        "annotation_meta": {
            "annotator": "bob",
            "annotator_role": "Abstractor",
            "annotation_date": "2025-01-02",
            "dataset_version": "v0",
            "key": "K1",
        },
        "objects": [],
    }
    db.upsert_annotation(user["id"], "patient_001::note_001", json.dumps(payload))
    rows = db.list_annotations(user_id=user["id"], document_key="patient_001::note_001")
    assert len(rows) == 1
    assert json.loads(rows[0]["annotation_json"]) == payload

    payload["objects"].append({"object_index": 1, "action": "Created", "object_type": "Lab"})
    db.upsert_annotation(user["id"], "patient_001::note_001", json.dumps(payload), status="In Review")
    rows = db.list_annotations(user_id=user["id"], document_key="patient_001::note_001")
    assert len(rows) == 1
    assert json.loads(rows[0]["annotation_json"])["objects"]
    assert rows[0]["status"] == "In Review"


def test_status_updates_and_comments(tmp_path):
    setup_temp_db(tmp_path)
    db.create_user("alice", "pw1")
    db.create_user("reviewer", "pw2")
    alice = db.authenticate_user("alice", "pw1")
    reviewer = db.authenticate_user("reviewer", "pw2")
    doc_key = "patient_x::note_y"
    payload = {
        "patient_id": "patient_x",
        "source_id": "note_y",
        "source_type": "oncology",
        "document_date": "2025-02-01",
        "annotation_meta": {
            "annotator": "alice",
            "annotator_role": "Abstractor",
            "annotation_date": "2025-02-02",
            "dataset_version": "v0",
            "key": "K1",
        },
        "objects": [],
    }
    db.upsert_annotation(alice["id"], doc_key, json.dumps(payload), status="Assigned")
    rows = db.list_annotations(document_key=doc_key)
    assert rows[0]["status"] == "Assigned"
    db.update_annotation_status(rows[0]["id"], "Accepted", reviewer_id=reviewer["id"], reviewer_notes="LGTM")
    rows = db.list_annotations(document_key=doc_key)
    assert rows[0]["status"] == "Accepted"
    assert rows[0]["reviewer_id"] == reviewer["id"]
    assert rows[0]["reviewer_notes"] == "LGTM"

    db.create_comment(rows[0]["id"], reviewer["id"], "Please double check lab units")
    comments = db.list_comments(rows[0]["id"])
    assert comments
    assert comments[0]["message"] == "Please double check lab units"
    assert comments[0]["username"] == "reviewer"
