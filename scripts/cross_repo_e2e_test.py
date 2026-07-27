#!/usr/bin/env python3
"""
Phase 3D Final Acceptance — Cross Repository E2E Digital Thread Test
Builds KnowGraphGo CLI, creates temp SQLite DB, applies event sequence,
verifies Digital Thread path + Idempotent Replay.
"""

import json
import os
import subprocess
import sys
import tempfile
import time


def build_cli():
    """Build KnowGraphGo CLI binary."""
    kg_dir = os.path.join(os.path.dirname(__file__), "..", "KnowGraphGo")
    result = subprocess.run(
        ["go", "build", "-o", "knowgraph.exe", "./cmd/knowgraph/"],
        cwd=kg_dir, capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        print(f"BUILD FAILED:\n{result.stderr}")
        sys.exit(1)
    cli_path = os.path.join(kg_dir, "knowgraph.exe")
    print(f"[PASS] CLI built: {cli_path}")
    return cli_path


def init_db(cli_path, db_path):
    result = subprocess.run(
        [cli_path, "--dsn", db_path, "init"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"INIT FAILED:\n{result.stderr}")
        sys.exit(1)
    print(f"[PASS] SQLite DB initialized: {db_path}")


def apply_event(cli_path, db_path, event_data):
    """Apply a clinical event via stdin pipe."""
    result = subprocess.run(
        [cli_path, "--dsn", db_path, "clinical", "apply"],
        input=json.dumps(event_data),
        capture_output=True, text=True, timeout=30
    )
    print(f"  apply stdout: {result.stdout[:200]}")
    if result.returncode != 0:
        print(f"  apply stderr: {result.stderr[:200]}")
        return False
    return True


def query_count(cli_path, db_path):
    """Query entity and relation counts via the check command."""
    result = subprocess.run(
        [cli_path, "--dsn", db_path, "--json", "check"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return {"entities": 0, "relations": 0}
    try:
        data = json.loads(result.stdout)
        return {"entities": data.get("total_entities", 0), "relations": data.get("total_edges", 0)}
    except json.JSONDecodeError:
        return {"entities": 0, "relations": 0}


def query_path(cli_path, db_path, from_id, to_id):
    result = subprocess.run(
        [cli_path, "--dsn", db_path, "query", "path", from_id, to_id],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout, result.returncode


def get_entity_id(cli_path, db_path, prop_key, prop_value):
    """Get graph entity ID by property query (e.g. patient_id=P001)."""
    result = subprocess.run(
        [cli_path, "--dsn", db_path, "--json", "query", "prop", f"{prop_key}={prop_value}"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        entities = data.get("entities", [])
        if entities:
            return entities[0].get("id")
    except (json.JSONDecodeError, KeyError, IndexError):
        pass
    return None


def create_event_json(entity_type, event_type, aggregate_id, payload, correlation_id=None, causation_id=None):
    event = {
        "event_id": f"evt-{aggregate_id}-{event_type}-{int(time.time())}",
        "event_type": event_type,
        "aggregate_type": entity_type,
        "aggregate_id": aggregate_id,
        "occurred_at": "2026-07-27T00:00:00Z",
        "payload": payload
    }
    if correlation_id:
        event["correlation_id"] = correlation_id
    if causation_id:
        event["causation_id"] = causation_id
    return event


def main():
    print("=" * 60)
    print("Phase 3D Cross Repository E2E Digital Thread Test")
    print("=" * 60)

    # Build CLI
    cli_path = build_cli()

    # Temp DB
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(cli_path, db_path)
        patient_id = "P001"
        rec_id = "REC-001"
        decision_id = "DC-001"
        consensus_id = "CON-001"

        # --- FIRST APPLY ---
        print("\n--- Step 1: Apply patient.created ---")
        evt = create_event_json("patient", "patient.created", patient_id, {
            "patient_id": patient_id, "display_name": "ANON", "sex": "F",
            "age_range": "40-50", "cancer_type": "BRCA", "source_system": "EHR",
            "source_id": "SRC-001"
        })
        ok1 = apply_event(cli_path, db_path, evt)
        print(f"  patient.created: {'PASS' if ok1 else 'FAIL'}")

        print("\n--- Step 2: Apply recommendation.created ---")
        evt2 = create_event_json("recommendation", "recommendation.created", rec_id, {
            "recommendation_id": rec_id, "patient_id": patient_id,
            "title": "Recommendation for P001",
            "recommended_drugs": [{"drug_id": "DRUG-001", "drug_name": "Olaparib"}],
            "evidence_references": [{"evidence_id": "EV-001", "citation": "Study XYZ"}],
            "rank": 1, "score": 0.95
        }, correlation_id=f"corr-{patient_id}")
        ok2 = apply_event(cli_path, db_path, evt2)
        print(f"  recommendation.created: {'PASS' if ok2 else 'FAIL'}")

        print("\n--- Step 3: Apply clinical_decision.created ---")
        evt3 = create_event_json("clinical_decision", "clinical_decision.created", decision_id, {
            "decision_id": decision_id, "patient_id": patient_id,
            "description": "Clinical decision for P001",
            "recommendation_id": rec_id, "decision_type": "APPROVED",
            "rationale": "Based on guidelines",
            "evidence_references": [{"evidence_id": "EV-001", "citation": "Study XYZ"}]
        }, correlation_id=f"corr-{patient_id}", causation_id=f"evt-{rec_id}")
        ok3 = apply_event(cli_path, db_path, evt3)
        print(f"  clinical_decision.created: {'PASS' if ok3 else 'FAIL'}")

        print("\n--- Step 4: Apply tumor_board_consensus.created ---")
        evt4 = create_event_json("tumor_board_consensus", "tumor_board_consensus.created", consensus_id, {
            "consensus_id": consensus_id, "patient_id": patient_id,
            "title": "Consensus for P001",
            "clinical_decision_id": decision_id, "final_recommendation": "Approve Olaparib",
            "consensus_status": "AGREED", "consensus_score": 0.92,
            "supporting_evidence": [{"evidence_id": "EV-001"}],
            "specialist_opinions": [{"opinion_id": "OP-001", "specialist": "Dr. Smith", "specialty": "ONCOLOGY", "content": "Agree with recommendation"}],
            "participating_specialties": ["ONCOLOGY", "RADIOLOGY"]
        }, correlation_id=f"corr-{patient_id}", causation_id=f"evt-{decision_id}")
        ok4 = apply_event(cli_path, db_path, evt4)
        print(f"  tumor_board_consensus.created: {'PASS' if ok4 else 'FAIL'}")

        all_ok = ok1 and ok2 and ok3 and ok4
        print(f"\n>>> All events applied: {'PASS' if all_ok else 'FAIL'}")

        # --- DIGITAL THREAD PATH VERIFICATION ---
        print("\n--- Digital Thread Path Verification ---")
        patient_gid = get_entity_id(cli_path, db_path, "patient_id", patient_id)
        rec_gid = get_entity_id(cli_path, db_path, "recommendation_id", rec_id)
        decision_gid = get_entity_id(cli_path, db_path, "decision_id", decision_id)
        consensus_gid = get_entity_id(cli_path, db_path, "consensus_id", consensus_id)

        print(f"  Patient graph ID:       {patient_gid}")
        print(f"  Recommendation graph ID: {rec_gid}")
        print(f"  Decision graph ID:       {decision_gid}")
        print(f"  Consensus graph ID:      {consensus_gid}")

        path_checks = []
        if patient_gid and rec_gid:
            _, rc = query_path(cli_path, db_path, patient_gid, rec_gid)
            path_checks.append(rc == 0)
            print(f"  Patient → Recommendation path: {'PASS' if rc == 0 else 'FAIL'}")
        else:
            path_checks.append(False)
            print(f"  Patient → Recommendation path: FAIL (missing IDs)")

        if rec_gid and decision_gid:
            _, rc = query_path(cli_path, db_path, rec_gid, decision_gid)
            path_checks.append(rc == 0)
            print(f"  Recommendation → Decision path: {'PASS' if rc == 0 else 'FAIL'}")
        else:
            path_checks.append(False)
            print(f"  Recommendation → Decision path: FAIL (missing IDs)")

        if decision_gid and consensus_gid:
            _, rc = query_path(cli_path, db_path, decision_gid, consensus_gid)
            path_checks.append(rc == 0)
            print(f"  Decision → Consensus path: {'PASS' if rc == 0 else 'FAIL'}")
        else:
            path_checks.append(False)
            print(f"  Decision → Consensus path: FAIL (missing IDs)")

        path_ok = all(path_checks)
        print(f">>> Digital Thread Path: {'PASS' if path_ok else 'FAIL'}")

        # Count after first apply
        count1 = query_count(cli_path, db_path)
        print(f"Count after 1st apply: entities={count1.get('entities', '?')}, relations={count1.get('relations', '?')}")

        # --- IDEMPOTENT REPLAY ---
        print("\n--- Step 5: Idempotent Replay (apply same events again) ---")
        for i, (evt_data, label) in enumerate([
            (evt, "patient.created"),
            (evt2, "recommendation.created"),
            (evt3, "clinical_decision.created"),
            (evt4, "tumor_board_consensus.created"),
        ]):
            ok = apply_event(cli_path, db_path, evt_data)
            print(f"  replay {label}: {'PASS' if ok else 'FAIL'}")

        count2 = query_count(cli_path, db_path)
        print(f"Count after 2nd apply (replay): entities={count2.get('entities', '?')}, relations={count2.get('relations', '?')}")

        # Verify idempotent
        if count2.get("entities") == count1.get("entities") and count2.get("relations") == count1.get("relations"):
            print(">>> Idempotent Replay: PASS (counts unchanged)")
        else:
            print(f">>> Idempotent Replay: FAIL (entities {count1.get('entities')}→{count2.get('entities')}, relations {count1.get('relations')}→{count2.get('relations')})")

        # --- UPDATE UPSERT ---
        print("\n--- Step 6: Update Upsert (apply patient.updated) ---")
        evt_update = create_event_json("patient", "patient.updated", patient_id, {
            "patient_id": patient_id, "display_name": "ANON-UPDATED", "sex": "F",
            "age_range": "40-50", "cancer_type": "BRCA", "source_system": "EHR",
            "source_id": "SRC-001"
        }, correlation_id=f"corr-{patient_id}", causation_id=f"evt-{patient_id}-v2")
        ok_update = apply_event(cli_path, db_path, evt_update)
        print(f"  patient.updated: {'PASS' if ok_update else 'FAIL'}")

        count3 = query_count(cli_path, db_path)
        print(f"Count after update: entities={count3.get('entities', '?')}, relations={count3.get('relations', '?')}")
        if count3.get("entities") == count2.get("entities"):
            print(">>> Update Upsert: PASS (entity count unchanged)")
        else:
            print(f">>> Update Upsert: FAIL (entities {count2.get('entities')}→{count3.get('entities')})")

        # --- SUMMARY ---
        print("\n" + "=" * 60)
        passed = all([all_ok, path_ok,
                     count2.get("entities") == count1.get("entities"),
                     count2.get("relations") == count1.get("relations"),
                     count3.get("entities") == count2.get("entities")])
        print(f"RESULT: {'ALL E2E TESTS PASSED [PASS]' if passed else 'SOME TESTS FAILED [FAIL]'}")
        print(f"  Events applied: {'PASS' if all_ok else 'FAIL'}")
        print(f"  Digital Thread Path: {'PASS' if path_ok else 'FAIL'}")
        print(f"  Idempotent Replay: {'PASS' if count2.get('entities') == count1.get('entities') else 'FAIL'}")
        print(f"  Update Upsert: {'PASS' if count3.get('entities') == count2.get('entities') else 'FAIL'}")

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
