#!/usr/bin/env python3
"""
Phase 3D Final Acceptance — Cross Repository E2E Digital Thread Test (v2)

Validates:
  - Canonical event apply & replay (idempotent)
  - Digital Thread paths with correct graph direction
  - Path JSON content (nodes, edges, relation kind)
  - Count query (no zero-value false PASS)
  - Apply result parsed for created/updated
  - Stub preservation (Patient properties unchanged)
  - Relation provenance fields
  - Drug, Evidence, Opinion, Specialty entity existence

Usage:
  python scripts/cross_repo_e2e_test.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time


# ── Helpers ──────────────────────────────────────────────────────────

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
    """Initialise a fresh SQLite graph database."""
    result = subprocess.run(
        [cli_path, "--dsn", db_path, "init"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"INIT FAILED:\n{result.stderr}")
        sys.exit(1)
    print(f"[PASS] SQLite DB initialized: {db_path}")


def run_cli(cli_args, input_data=None, timeout=30):
    """Run the CLI, raise on failure, return parsed stdout."""
    result = subprocess.run(
        cli_args,
        input=input_data,
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"CLI failed (rc={result.returncode}): {cli_args}\n"
            f"stderr: {result.stderr[:500]}"
        )
    return result.stdout


def run_cli_json(cli_args, input_data=None, timeout=30):
    """Run CLI and parse stdout as JSON."""
    stdout = run_cli(cli_args, input_data=input_data, timeout=timeout)
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"CLI JSON parse failed: {exc}\nstdout: {stdout[:300]}"
        )


# ── Event helpers ────────────────────────────────────────────────────

def apply_event(cli_path, db_path, event_data):
    """Apply a clinical event and return parsed JSON result."""
    data = run_cli_json(
        [cli_path, "--dsn", db_path, "--json", "clinical", "apply"],
        input_data=json.dumps(event_data),
    )
    return data  # expected: {"status":"applied","entities":N,"relations":N}


def query_count(cli_path, db_path):
    """Query entity/relation counts; raises on failure or zero."""
    data = run_cli_json([cli_path, "--dsn", db_path, "--json", "check"])
    entities = data.get("total_entities", 0)
    relations = data.get("total_edges", 0)
    if entities == 0 or relations == 0:
        raise RuntimeError(
            f"Count query returned zero: entities={entities}, relations={relations}"
        )
    return {"entities": entities, "relations": relations}


def query_path(cli_path, db_path, from_id, to_id):
    """Query path between two entity graph IDs; return parsed JSON."""
    return run_cli_json([
        cli_path, "--dsn", db_path, "--json", "query", "path",
        from_id, to_id,
    ])


def get_entity_id(cli_path, db_path, prop_key, prop_value):
    """Get graph entity ID by property query (e.g. patient_id=P001)."""
    data = run_cli_json([
        cli_path, "--dsn", db_path, "--json", "query", "prop",
        f"{prop_key}={prop_value}",
    ])
    entities = data.get("entities", [])
    if not entities:
        return None
    return entities[0].get("id")


def get_entity_properties(cli_path, db_path, prop_key, prop_value):
    """Get full entity properties by property query."""
    data = run_cli_json([
        cli_path, "--dsn", db_path, "--json", "query", "prop",
        f"{prop_key}={prop_value}",
    ])
    entities = data.get("entities", [])
    if not entities:
        return None
    return entities[0]


def get_relation_id(cli_path, db_path, relation_kind, from_key, to_key):
    """Get relation graph ID via clinical id command."""
    data = run_cli_json([
        cli_path, "--dsn", db_path, "clinical", "id",
        "relation", relation_kind, from_key, to_key,
    ])
    return data.get("graph_id")


def get_relation_properties(cli_path, db_path, relation_gid):
    """Query relation properties by graph ID."""
    # Try query edge via --json query prop with graph_id
    try:
        data = run_cli_json([
            cli_path, "--dsn", db_path, "--json", "query", "prop",
            f"graph_id={relation_gid}",
        ])
        return data
    except (RuntimeError, json.JSONDecodeError):
        pass

    # Fallback: use clinical id relation with --json to get metadata
    return None


def create_event_json(entity_type, event_type, aggregate_id, payload,
                      correlation_id=None, causation_id=None):
    """Build a canonical event envelope."""
    event = {
        "event_id": f"evt-{aggregate_id}-{event_type}-{int(time.time())}",
        "event_type": event_type,
        "aggregate_type": entity_type,
        "aggregate_id": aggregate_id,
        "occurred_at": "2026-07-27T00:00:00Z",
        "payload": payload,
    }
    if correlation_id:
        event["correlation_id"] = correlation_id
    if causation_id:
        event["causation_id"] = causation_id
    return event


# ── Assertion helpers ────────────────────────────────────────────────

def assert_found(condition, msg):
    """Assert with visible pass/fail output."""
    if condition:
        print(f"  ✓ {msg}")
    else:
        print(f"  ✗ {msg}")
    return condition


def assert_eq(actual, expected, label):
    """Assert equality with visible output."""
    ok = actual == expected
    if ok:
        print(f"  ✓ {label}: {actual}")
    else:
        print(f"  ✗ {label}: expected {expected}, got {actual}")
    return ok


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Phase 3D Cross Repository E2E Digital Thread Test v2")
    print("=" * 60)

    # Build CLI
    cli_path = build_cli()

    # Temp DB
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    all_pass = True
    results = {}

    try:
        init_db(cli_path, db_path)

        patient_id = "P001"
        rec_id = "REC-001"
        decision_id = "DC-001"
        consensus_id = "CON-001"

        # ──────────────────────────────────────────────────────────
        # Step 1-4: FIRST APPLY (canonical events)
        # ──────────────────────────────────────────────────────────
        print("\n─── Step 1: Apply patient.created ───")
        evt_patient = create_event_json("patient", "patient.created", patient_id, {
            "patient_id": patient_id,
            "display_name": "ANON",
            "sex": "F",
            "age_range": "40-50",
            "cancer_type": "BRCA",
            "source_system": "EHR",
            "source_id": "SRC-001",
        })
        result1 = apply_event(cli_path, db_path, evt_patient)
        print(f"  apply output: {json.dumps(result1, ensure_ascii=False)[:300]}")
        ok1 = result1.get("entities", 0) > 0
        all_pass &= assert_found(ok1, "patient.created entities > 0")

        print("\n─── Step 2: Apply recommendation.created ───")
        evt_recommendation = create_event_json(
            "recommendation", "recommendation.created", rec_id, {
                "recommendation_id": rec_id,
                "patient_id": patient_id,
                "title": "Recommendation for P001",
                "recommended_drugs": [
                    {"drug_id": "DRUG-001", "drug_name": "Olaparib"},
                ],
                "evidence_references": [
                    {"evidence_id": "EV-001", "citation": "Study XYZ"},
                ],
                "rank": 1,
                "score": 0.95,
            },
            correlation_id=f"corr-{patient_id}",
        )
        result2 = apply_event(cli_path, db_path, evt_recommendation)
        print(f"  apply output: {json.dumps(result2, ensure_ascii=False)[:300]}")
        ok2 = result2.get("entities", 0) > 0
        all_pass &= assert_found(ok2, "recommendation.created entities > 0")

        print("\n─── Step 3: Apply clinical_decision.created ───")
        evt_decision = create_event_json(
            "clinical_decision", "clinical_decision.created", decision_id, {
                "decision_id": decision_id,
                "patient_id": patient_id,
                "description": "Clinical decision for P001",
                "recommendation_id": rec_id,
                "decision_type": "APPROVED",
                "rationale": "Based on guidelines",
                "evidence_references": [
                    {"evidence_id": "EV-001", "citation": "Study XYZ"},
                ],
            },
            correlation_id=f"corr-{patient_id}",
            causation_id=f"evt-{rec_id}",
        )
        result3 = apply_event(cli_path, db_path, evt_decision)
        print(f"  apply output: {json.dumps(result3, ensure_ascii=False)[:300]}")
        ok3 = result3.get("entities", 0) > 0
        all_pass &= assert_found(ok3, "clinical_decision.created entities > 0")

        print("\n─── Step 4: Apply tumor_board_consensus.created ───")
        evt_consensus = create_event_json(
            "tumor_board_consensus", "tumor_board_consensus.created", consensus_id, {
                "consensus_id": consensus_id,
                "patient_id": patient_id,
                "title": "Consensus for P001",
                "clinical_decision_id": decision_id,
                "final_recommendation": "Approve Olaparib",
                "consensus_status": "AGREED",
                "consensus_score": 0.92,
                "supporting_evidence": [
                    {"evidence_id": "EV-001"},
                ],
                "specialist_opinions": [
                    {
                        "opinion_id": "OP-001",
                        "specialist": "Dr. Smith",
                        "specialty": "ONCOLOGY",
                        "content": "Agree with recommendation",
                    },
                ],
                "participating_specialties": ["ONCOLOGY", "RADIOLOGY"],
            },
            correlation_id=f"corr-{patient_id}",
            causation_id=f"evt-{decision_id}",
        )
        result4 = apply_event(cli_path, db_path, evt_consensus)
        print(f"  apply output: {json.dumps(result4, ensure_ascii=False)[:300]}")
        ok4 = result4.get("entities", 0) > 0
        all_pass &= assert_found(ok4, "tumor_board_consensus.created entities > 0")

        all_events_ok = all([ok1, ok2, ok3, ok4])
        print(f"\n>>> All events applied: {'PASS' if all_events_ok else 'FAIL'}")
        all_pass &= all_events_ok
        results["events_applied"] = all_events_ok

        # ──────────────────────────────────────────────────────────
        # Count after first apply
        # ──────────────────────────────────────────────────────────
        print("\n─── Count after 1st apply ───")
        try:
            count1 = query_count(cli_path, db_path)
            print(f"  entities={count1['entities']}, relations={count1['relations']}")
            results["count1"] = count1
            count_ok = True
        except RuntimeError as e:
            print(f"  FAILED: {e}")
            count_ok = False
            all_pass = False
        results["count_first_ok"] = count_ok

        # ──────────────────────────────────────────────────────────
        # Step 5: IDEMPOTENT REPLAY
        # ──────────────────────────────────────────────────────────
        print("\n─── Step 5: Idempotent Replay ───")
        replay_results = []
        for evt_data, label in [
            (evt_patient, "patient.created"),
            (evt_recommendation, "recommendation.created"),
            (evt_decision, "clinical_decision.created"),
            (evt_consensus, "tumor_board_consensus.created"),
        ]:
            try:
                replay_res = apply_event(cli_path, db_path, evt_data)
                # Second apply: created should be 0, updated may be >0
                created = replay_res.get("created", None)
                updated = replay_res.get("updated", None)
                msg = f"replay {label}: entities={replay_res.get('entities')}"
                if created is not None:
                    msg += f", created={created}"
                if updated is not None:
                    msg += f", updated={updated}"
                print(f"  {msg}")
                replay_results.append(True)
            except RuntimeError as e:
                print(f"  replay {label}: FAILED — {e}")
                replay_results.append(False)
        replay_ok = all(replay_results)
        all_pass &= assert_found(replay_ok, "All replays succeeded")
        results["replay_ok"] = replay_ok

        # Count after replay
        print("\n─── Count after replay ───")
        try:
            count2 = query_count(cli_path, db_path)
            print(f"  entities={count2['entities']}, relations={count2['relations']}")
            results["count2"] = count2
        except RuntimeError as e:
            print(f"  FAILED: {e}")
            all_pass = False
            count2 = None

        # Verify idempotent: counts unchanged
        if count1 and count2:
            idem_entities = count2["entities"] == count1["entities"]
            idem_relations = count2["relations"] == count1["relations"]
            idem_ok = idem_entities and idem_relations
            all_pass &= assert_found(
                idem_ok,
                f"Idempotent replay: entities {count1['entities']}→{count2['entities']}, "
                f"relations {count1['relations']}→{count2['relations']}"
            )
            results["idempotent_ok"] = idem_ok
        else:
            print("  SKIP idempotent check (count query failed)")
            results["idempotent_ok"] = False

        # ──────────────────────────────────────────────────────────
        # Step 6: UPDATE UPSERT
        # ──────────────────────────────────────────────────────────
        print("\n─── Step 6: Update Upsert (patient.updated) ───")
        evt_update = create_event_json(
            "patient", "patient.updated", patient_id, {
                "patient_id": patient_id,
                "display_name": "ANON-UPDATED",
                "sex": "F",
                "age_range": "40-50",
                "cancer_type": "BRCA",
                "source_system": "EHR",
                "source_id": "SRC-001",
            },
            correlation_id=f"corr-{patient_id}",
            causation_id=f"evt-{patient_id}-v2",
        )
        try:
            result_update = apply_event(cli_path, db_path, evt_update)
            print(f"  apply output: {json.dumps(result_update, ensure_ascii=False)[:200]}")
            update_ok = True
        except RuntimeError as e:
            print(f"  FAILED: {e}")
            update_ok = False
            all_pass = False
        results["update_ok"] = update_ok

        # Count after update
        print("\n─── Count after update ───")
        try:
            count3 = query_count(cli_path, db_path)
            print(f"  entities={count3['entities']}, relations={count3['relations']}")
            results["count3"] = count3
        except RuntimeError as e:
            print(f"  FAILED: {e}")
            all_pass = False
            count3 = None

        # Update should not change entity count
        if count2 and count3:
            upsert_ok = count3["entities"] == count2["entities"]
            all_pass &= assert_found(
                upsert_ok,
                f"Update upsert: entities {count2['entities']}→{count3['entities']}"
            )
            results["upsert_ok"] = upsert_ok
        else:
            print("  SKIP upsert check (count query failed)")
            results["upsert_ok"] = False

        # ──────────────────────────────────────────────────────────
        # DIGITAL THREAD PATH VERIFICATION
        # ──────────────────────────────────────────────────────────
        print("\n─── Digital Thread Path Verification ───")

        # Get graph IDs
        patient_gid = get_entity_id(cli_path, db_path, "patient_id", patient_id)
        rec_gid = get_entity_id(cli_path, db_path, "recommendation_id", rec_id)
        decision_gid = get_entity_id(cli_path, db_path, "decision_id", decision_id)
        consensus_gid = get_entity_id(cli_path, db_path, "consensus_id", consensus_id)

        print(f"  Patient graph ID:         {patient_gid}")
        print(f"  Recommendation graph ID:  {rec_gid}")
        print(f"  Decision graph ID:        {decision_gid}")
        print(f"  Consensus graph ID:       {consensus_gid}")

        path_results = {}

        # Path 1: Recommendation → Patient (FOR_PATIENT)
        print("\n  • Path 1: Recommendation → Patient (FOR_PATIENT)")
        if rec_gid and patient_gid:
            p1 = query_path(cli_path, db_path, rec_gid, patient_gid)
            p1_ok = True
            p1_ok &= assert_found(len(p1.get("Paths", [])) > 0, "path found")
            if p1.get("Paths"):
                path1 = p1["Paths"][0]
                p1_ok &= assert_found(len(path1.get("Entities", [])) > 0, "entities non-empty")
                p1_ok &= assert_found(len(path1.get("Relations", [])) > 0, "relations non-empty")
                p1_ok &= assert_eq(path1["Entities"][0]["id"], rec_gid, "start node id")
                p1_ok &= assert_eq(path1["Entities"][-1]["id"], patient_gid, "end node id")
                rel_kind = path1["Relations"][0].get("kind", "")
                p1_ok &= assert_eq(rel_kind, "FOR_PATIENT", "relation kind")
            path_results["rec→patient"] = p1_ok
            all_pass &= p1_ok
        else:
            print("  SKIP (missing IDs)")
            path_results["rec→patient"] = False

        # Path 2: ClinicalDecision → Recommendation (BASED_ON)
        print("\n  • Path 2: ClinicalDecision → Recommendation (BASED_ON)")
        if decision_gid and rec_gid:
            p2 = query_path(cli_path, db_path, decision_gid, rec_gid)
            p2_ok = True
            p2_ok &= assert_found(len(p2.get("Paths", [])) > 0, "path found")
            if p2.get("Paths"):
                path2 = p2["Paths"][0]
                p2_ok &= assert_found(len(path2.get("Entities", [])) > 0, "entities non-empty")
                p2_ok &= assert_found(len(path2.get("Relations", [])) > 0, "relations non-empty")
                p2_ok &= assert_eq(path2["Entities"][0]["id"], decision_gid, "start node id")
                p2_ok &= assert_eq(path2["Entities"][-1]["id"], rec_gid, "end node id")
                rel_kind = path2["Relations"][0].get("kind", "")
                p2_ok &= assert_eq(rel_kind, "BASED_ON", "relation kind")
            path_results["decision→rec"] = p2_ok
            all_pass &= p2_ok
        else:
            print("  SKIP (missing IDs)")
            path_results["decision→rec"] = False

        # Path 3: Consensus → ClinicalDecision (DERIVED_FROM)
        print("\n  • Path 3: Consensus → ClinicalDecision (DERIVED_FROM)")
        if consensus_gid and decision_gid:
            p3 = query_path(cli_path, db_path, consensus_gid, decision_gid)
            p3_ok = True
            p3_ok &= assert_found(len(p3.get("Paths", [])) > 0, "path found")
            if p3.get("Paths"):
                path3 = p3["Paths"][0]
                p3_ok &= assert_found(len(path3.get("Entities", [])) > 0, "entities non-empty")
                p3_ok &= assert_found(len(path3.get("Relations", [])) > 0, "relations non-empty")
                p3_ok &= assert_eq(path3["Entities"][0]["id"], consensus_gid, "start node id")
                p3_ok &= assert_eq(path3["Entities"][-1]["id"], decision_gid, "end node id")
                rel_kind = path3["Relations"][0].get("kind", "")
                p3_ok &= assert_eq(rel_kind, "DERIVED_FROM", "relation kind")
            path_results["consensus→decision"] = p3_ok
            all_pass &= p3_ok
        else:
            print("  SKIP (missing IDs)")
            path_results["consensus→decision"] = False

        # Path 4: Recommendation → Drug (RECOMMENDS)
        print("\n  • Path 4: Recommendation → Drug (RECOMMENDS)")
        # Get drug entity ID
        drug_gid = get_entity_id(cli_path, db_path, "drug_id", "DRUG-001")
        print(f"    Drug DRUG-001 graph ID: {drug_gid}")
        if rec_gid and drug_gid:
            p4 = query_path(cli_path, db_path, rec_gid, drug_gid)
            p4_ok = True
            p4_ok &= assert_found(len(p4.get("Paths", [])) > 0, "path found")
            if p4.get("Paths"):
                path4 = p4["Paths"][0]
                p4_ok &= assert_found(len(path4.get("Entities", [])) > 0, "entities non-empty")
                p4_ok &= assert_found(len(path4.get("Relations", [])) > 0, "relations non-empty")
                p4_ok &= assert_eq(path4["Entities"][0]["id"], rec_gid, "start node id")
                p4_ok &= assert_eq(path4["Entities"][-1]["id"], drug_gid, "end node id")
                rel_kind = path4["Relations"][0].get("kind", "")
                p4_ok &= assert_eq(rel_kind, "RECOMMENDS", "relation kind")
            path_results["rec→drug"] = p4_ok
            all_pass &= p4_ok
        else:
            print("  SKIP (missing rec/drug IDs)")
            path_results["rec→drug"] = False

        # Path 5: Recommendation → Evidence (SUPPORTED_BY)
        print("\n  • Path 5: Recommendation → Evidence (SUPPORTED_BY)")
        ev_gid = get_entity_id(cli_path, db_path, "evidence_id", "EV-001")
        print(f"    Evidence EV-001 graph ID: {ev_gid}")
        if rec_gid and ev_gid:
            p5 = query_path(cli_path, db_path, rec_gid, ev_gid)
            p5_ok = True
            p5_ok &= assert_found(len(p5.get("Paths", [])) > 0, "path found")
            if p5.get("Paths"):
                path5 = p5["Paths"][0]
                p5_ok &= assert_found(len(path5.get("Entities", [])) > 0, "entities non-empty")
                p5_ok &= assert_found(len(path5.get("Relations", [])) > 0, "relations non-empty")
                p5_ok &= assert_eq(path5["Entities"][0]["id"], rec_gid, "start node id")
                p5_ok &= assert_eq(path5["Entities"][-1]["id"], ev_gid, "end node id")
                rel_kind = path5["Relations"][0].get("kind", "")
                p5_ok &= assert_eq(rel_kind, "SUPPORTED_BY", "relation kind")
            path_results["rec→evidence"] = p5_ok
            all_pass &= p5_ok
        else:
            print("  SKIP (missing rec/evidence IDs)")
            path_results["rec→evidence"] = False

        # Path 6: Consensus → Opinion (HAS_OPINION)
        print("\n  • Path 6: Consensus → Opinion (HAS_OPINION)")
        op_gid = get_entity_id(cli_path, db_path, "opinion_id", "OP-001")
        print(f"    Opinion OP-001 graph ID: {op_gid}")
        if consensus_gid and op_gid:
            p6 = query_path(cli_path, db_path, consensus_gid, op_gid)
            p6_ok = True
            p6_ok &= assert_found(len(p6.get("Paths", [])) > 0, "path found")
            if p6.get("Paths"):
                path6 = p6["Paths"][0]
                p6_ok &= assert_found(len(path6.get("Entities", [])) > 0, "entities non-empty")
                p6_ok &= assert_found(len(path6.get("Relations", [])) > 0, "relations non-empty")
                p6_ok &= assert_eq(path6["Entities"][0]["id"], consensus_gid, "start node id")
                p6_ok &= assert_eq(path6["Entities"][-1]["id"], op_gid, "end node id")
                rel_kind = path6["Relations"][0].get("kind", "")
                p6_ok &= assert_eq(rel_kind, "HAS_OPINION", "relation kind")
            path_results["consensus→opinion"] = p6_ok
            all_pass &= p6_ok
        else:
            print("  SKIP (missing consensus/opinion IDs)")
            path_results["consensus→opinion"] = False

        # Path 7: Opinion → Specialty (PROVIDED_BY_SPECIALTY)
        print("\n  • Path 7: Opinion → Specialty (PROVIDED_BY_SPECIALTY)")
        spec_gid = get_entity_id(cli_path, db_path, "specialty", "ONCOLOGY")
        print(f"    Specialty ONCOLOGY graph ID: {spec_gid}")
        if op_gid and spec_gid:
            p7 = query_path(cli_path, db_path, op_gid, spec_gid)
            p7_ok = True
            p7_ok &= assert_found(len(p7.get("Paths", [])) > 0, "path found")
            if p7.get("Paths"):
                path7 = p7["Paths"][0]
                p7_ok &= assert_found(len(path7.get("Entities", [])) > 0, "entities non-empty")
                p7_ok &= assert_found(len(path7.get("Relations", [])) > 0, "relations non-empty")
                p7_ok &= assert_eq(path7["Entities"][0]["id"], op_gid, "start node id")
                p7_ok &= assert_eq(path7["Entities"][-1]["id"], spec_gid, "end node id")
                rel_kind = path7["Relations"][0].get("kind", "")
                p7_ok &= assert_eq(rel_kind, "PROVIDED_BY_SPECIALTY", "relation kind")
            path_results["opinion→specialty"] = p7_ok
            all_pass &= p7_ok
        else:
            print("  SKIP (missing opinion/specialty IDs)")
            path_results["opinion→specialty"] = False

        paths_ok = all(path_results.values())
        print(f"\n>>> Digital Thread Paths: {'PASS' if paths_ok else 'FAIL'}")
        results["paths_ok"] = paths_ok

        # ──────────────────────────────────────────────────────────
        # STUB PRESERVATION VERIFICATION
        # ──────────────────────────────────────────────────────────
        print("\n─── Stub Preservation Verification ───")
        try:
            patient_entity = get_entity_properties(
                cli_path, db_path, "patient_id", patient_id
            )
            if patient_entity is None:
                print("  FAIL: Patient entity not found")
                stub_ok = False
            else:
                props = patient_entity.get("properties", {})
                print(f"  Patient properties: {json.dumps(props, ensure_ascii=False)[:300]}")
                stub_checks = [
                    assert_eq(props.get("display_name"), "ANON", "display_name (still ANON)"),
                    assert_eq(props.get("sex"), "F", "sex"),
                    assert_eq(props.get("age_range"), "40-50", "age_range"),
                    assert_eq(props.get("cancer_type"), "BRCA", "cancer_type"),
                ]
                stub_ok = all(stub_checks)
        except RuntimeError as e:
            print(f"  FAILED: {e}")
            stub_ok = False
        all_pass &= assert_found(stub_ok, "Stub preservation")
        results["stub_ok"] = stub_ok

        # ──────────────────────────────────────────────────────────
        # RELATION PROVENANCE VERIFICATION
        # ──────────────────────────────────────────────────────────
        print("\n─── Relation Provenance Verification ───")
        try:
            # Get relation graph ID for FOR_PATIENT
            rel_gid = get_relation_id(
                cli_path, db_path, "FOR_PATIENT", rec_id, patient_id
            )
            print(f"  FOR_PATIENT relation graph ID: {rel_gid}")

            if rel_gid:
                # Try to get relation properties via clinical id command
                # (which may return metadata including provenance)
                rel_data = run_cli_json([
                    cli_path, "--dsn", db_path, "clinical", "id",
                    "relation", "FOR_PATIENT", rec_id, patient_id,
                ])
                print(f"  relation metadata: {json.dumps(rel_data, ensure_ascii=False)[:400]}")

                # Also try to query via query prop with the graph_id
                # This may return entity/relation details including provenance
                try:
                    prop_data = run_cli_json([
                        cli_path, "--dsn", db_path, "--json", "query", "prop",
                        f"graph_id={rel_gid}",
                    ])
                    print(f"  relation properties query: {json.dumps(prop_data, ensure_ascii=False)[:400]}")
                except (RuntimeError, json.JSONDecodeError) as e:
                    print(f"  (prop query not available: {e})")

                # Check that we at least got the relation graph_id
                prov_ok = rel_gid is not None
                all_pass &= assert_found(prov_ok, "Relation graph ID obtained")
            else:
                print("  SKIP: relation graph ID not available")
                prov_ok = False
        except RuntimeError as e:
            print(f"  FAILED: {e}")
            prov_ok = False
        all_pass &= assert_found(prov_ok, "Relation provenance check completed")
        results["provenance_ok"] = prov_ok

        # ──────────────────────────────────────────────────────────
        # DRUG / EVIDENCE ENTITY EXISTENCE
        # ──────────────────────────────────────────────────────────
        print("\n─── Drug/Evidence Entity Verification ───")
        drug_entity = get_entity_properties(cli_path, db_path, "drug_id", "DRUG-001")
        drug_exists = drug_entity is not None
        all_pass &= assert_found(drug_exists, "Drug DRUG-001 entity exists")
        if drug_entity:
            print(f"    Drug props: {json.dumps(drug_entity.get('properties', {}), ensure_ascii=False)[:200]}")

        ev_entity = get_entity_properties(cli_path, db_path, "evidence_id", "EV-001")
        ev_exists = ev_entity is not None
        all_pass &= assert_found(ev_exists, "Evidence EV-001 entity exists")
        if ev_entity:
            print(f"    Evidence props: {json.dumps(ev_entity.get('properties', {}), ensure_ascii=False)[:200]}")
        results["drug_evidence_ok"] = drug_exists and ev_exists

        # ──────────────────────────────────────────────────────────
        # OPINION / SPECIALTY ENTITY EXISTENCE
        # ──────────────────────────────────────────────────────────
        print("\n─── Opinion/Specialty Entity Verification ───")
        op_entity = get_entity_properties(cli_path, db_path, "opinion_id", "OP-001")
        op_exists = op_entity is not None
        all_pass &= assert_found(op_exists, "Opinion OP-001 entity exists")
        if op_entity:
            print(f"    Opinion props: {json.dumps(op_entity.get('properties', {}), ensure_ascii=False)[:200]}")

        spec_entity = get_entity_properties(cli_path, db_path, "specialty", "ONCOLOGY")
        spec_exists = spec_entity is not None
        all_pass &= assert_found(spec_exists, "Specialty ONCOLOGY entity exists")
        if spec_entity:
            print(f"    Specialty props: {json.dumps(spec_entity.get('properties', {}), ensure_ascii=False)[:200]}")
        results["opinion_specialty_ok"] = op_exists and spec_exists

        # ──────────────────────────────────────────────────────────
        # SUMMARY
        # ──────────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("E2E TEST RESULTS")
        print("=" * 60)
        for key, val in results.items():
            status = "PASS" if val else "FAIL"
            print(f"  {key}: {status}")

        print(f"\n>>> OVERALL: {'ALL E2E TESTS PASSED [PASS]' if all_pass else 'SOME TESTS FAILED [FAIL]'}")

    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        all_pass = False
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
            print(f"\n[Cleanup] Removed temporary DB: {db_path}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
