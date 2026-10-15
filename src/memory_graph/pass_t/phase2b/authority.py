"""Read-only Phase 2a authority adapter for Phase 2b."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..external_dev.authority import load_authority
from ..external_dev.store import inventory
from .common import Phase2BBlocked, file_sha256, read_json, repository_root


DATASET_SHA256 = "ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c"
IMPORT_SHA256 = "3f85134d8c4f9f78e1b16bea3ec937225d37ff671e8caeb6620e401c3bb50a0b"
SIDECAR_FOLDER = "adjudicated_7e28b9edf80a8e4da88caa66"


@dataclass(frozen=True)
class Phase2BAuthority:
    root: Path
    phase2a: object
    dataset: dict
    dataset_path: Path
    items: dict
    records: dict
    exhaustive_sidecar: dict
    readiness: dict
    provenance: dict


def load_phase2b_authority() -> Phase2BAuthority:
    root = repository_root()
    phase2a = load_authority()
    store_root = root / "artifacts/pass_t/phase2a/v2/external_returns"
    imports = inventory(store_root, phase2a)
    if IMPORT_SHA256 not in imports:
        raise Phase2BBlocked("REQUIRED_IMMUTABLE_IMPORT_MISSING")
    dataset_path = store_root / "datasets" / DATASET_SHA256 / "external_dev_gt.json"
    receipt_path = dataset_path.parent / "completion_receipt.json"
    if not dataset_path.is_file() or file_sha256(dataset_path) != DATASET_SHA256:
        raise Phase2BBlocked("AUTHORITATIVE_DATASET_HASH_MISMATCH")
    receipt = read_json(receipt_path)
    if receipt.get("dataset_sha256") != DATASET_SHA256 or receipt.get("imports") != [IMPORT_SHA256]:
        raise Phase2BBlocked("AUTHORITATIVE_DATASET_RECEIPT_MISMATCH")
    dataset = read_json(dataset_path)
    if dataset.get("schema_version") != "PASS_T_EXTERNAL_DEV_GT_V1" or dataset.get("formal_eligible") != 0:
        raise Phase2BBlocked("AUTHORITATIVE_DATASET_CONTRACT_MISMATCH")
    records = {row["annotation_item_id"]: row for row in dataset["records"]}
    if set(records) != set(phase2a.items) or len(records) != 7:
        raise Phase2BBlocked("AUTHORITATIVE_ITEM_SET_MISMATCH")
    sidecar_path = root / "artifacts/pass_t/phase2a/v2/exhaustive_reviews" / SIDECAR_FOLDER / "adjudicated_dev_view.json"
    sidecar = read_json(sidecar_path)
    sidecar_records = {row["parent"]["annotation_item_id"]: row for row in sidecar.get("records", [])}
    if set(sidecar_records) != {"PT2A_eb60192e6986cb4f", "PT2A_c58b4df88a2f6801"}:
        raise Phase2BBlocked("EXHAUSTIVENESS_SIDECAR_ITEM_SET_MISMATCH")
    for row in sidecar_records.values():
        if row.get("exhaustive_review_readiness") is not False or row.get("binding_causality_status") != "CAUSALITY_UNVERIFIED":
            raise Phase2BBlocked("EXHAUSTIVENESS_SIDECAR_CONTRADICTION")
    readiness_path = root / "artifacts/pass_t/phase2a/v2/readiness_checks/20261013_negative_review/NEGATIVE_READINESS_REPORT.json"
    readiness = read_json(readiness_path)
    return Phase2BAuthority(
        root=root,
        phase2a=phase2a,
        dataset=dataset,
        dataset_path=dataset_path,
        items=phase2a.items,
        records=records,
        exhaustive_sidecar=sidecar,
        readiness=readiness,
        provenance={
            "dataset_path": dataset_path.relative_to(root).as_posix(),
            "dataset_sha256": DATASET_SHA256,
            "dataset_receipt_sha256": file_sha256(receipt_path),
            "import_sha256": IMPORT_SHA256,
            "policy_sha256": phase2a.receipt["policy_md_sha256"],
            "phase2a_manifest_sha256": file_sha256(root / "artifacts/pass_t/phase2a/v2/manifest.json"),
            "identity_resolution_sha256": file_sha256(root / "artifacts/pass_t/phase2a/v2/review_resolutions/identity_v1.json"),
            "exhaustiveness_sidecar_sha256": file_sha256(sidecar_path),
            "negative_readiness_sha256": file_sha256(readiness_path),
            "binding_causality_status": "CAUSALITY_UNVERIFIED",
        },
    )

