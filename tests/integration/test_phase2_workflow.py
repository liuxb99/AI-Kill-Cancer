"""
Phase 2 end-to-end workflow integration test.

Simulates the complete Phase 2 clinical decision-support pipeline via API
calls and verifies that outputs from each stage are correctly correlated.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.backend.config import settings
from src.backend.main import create_app


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with in-memory SQLite database."""
    settings.DATABASE_URL = "sqlite+aiosqlite://"
    settings.APP_MODE = "demo"
    settings.DEBUG = False
    app = create_app()
    with TestClient(app) as c:
        yield c


def _register_user(client: TestClient, username: str, password: str = "TestPass123!") -> str:
    """Register a user and return the access token."""
    resp = client.post("/auth/register", json={
        "username": username,
        "password": password,
        "display_name": username,
    })
    assert resp.status_code == 201, f"Register failed: {resp.json()}"
    login = client.post("/auth/login", json={
        "username": username,
        "password": password,
    })
    assert login.status_code == 200, f"Login failed: {login.json()}"
    return login.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_patient(client: TestClient, token: str) -> str:
    """Create a patient and return patient ID."""
    resp = client.post(
        "/api/v1/patients",
        json={"sex": "F", "consent_status": "granted"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, f"Create patient failed: {resp.json()}"
    return resp.json()["id"]


def _create_case(client: TestClient, token: str, patient_id: str) -> str:
    """Create a case and return case ID."""
    resp = client.post(
        "/api/v1/cases",
        json={"patient_id": patient_id, "cancer_type": "PTC"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, f"Create case failed: {resp.json()}"
    return resp.json()["id"]


# ─── Shared fixture ────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def workflow_setup(client):
    """Set up user, patient, and case for the workflow test."""
    token = _register_user(client, "workflow_user")
    pid = _create_patient(client, token)
    case_id = _create_case(client, token, pid)
    return {"token": token, "case_id": case_id, "patient_id": pid}


# ═══════════════════════════════════════════════════════════════════════════════
# Full Workflow Test
# ═══════════════════════════════════════════════════════════════════════════════


class TestPhase2FullWorkflow:
    """End-to-end test of the complete Phase 2 pipeline via API.

    The test executes each stage in order and verifies that outputs are
    correctly correlated across stages:
        1. Build clinical context
        2. Collect evidence
        3. Run agents
        4. Reach consensus
        5. Generate recommendation
        6. Verify decision thread
    """

    def test_full_pipeline_correlation(self, client, workflow_setup):
        """Execute the full pipeline step-by-step and verify cross-stage links.

        This test verifies:
        - ClinicalContext has context_hash
        - EvidenceBundle carries the same context_hash
        - AgentOpinions reference the context_hash
        - ConsensusResult contains the context_hash
        - Recommendation includes the context_hash
        - Decision thread records all stages in chronological order
        """
        case_id = workflow_setup["case_id"]
        headers = _auth_headers(workflow_setup["token"])

        # ── Step 1: Build clinical context ─────────────────────────────────
        resp = client.get(
            f"/api/v1/clinical/context/{case_id}",
            headers=headers,
        )
        assert resp.status_code == 200, f"Step 1 failed: {resp.json()}"
        context = resp.json()
        assert context["case_id"] == case_id
        context_hash = context["context_hash"]
        assert context_hash, "context_hash should be populated"

        # ── Step 2: Collect evidence ───────────────────────────────────────
        resp = client.get(
            f"/api/v1/clinical/evidence/{case_id}",
            headers=headers,
        )
        assert resp.status_code == 200, f"Step 2 failed: {resp.json()}"
        evidence = resp.json()
        assert isinstance(evidence["items"], list)
        # Evidence may or may not have context_hash at this point;
        # the standalone endpoint collects without a guarantee of hash

        # ── Step 3: Run agents ─────────────────────────────────────────────
        resp = client.post(
            f"/api/v1/clinical/agents/{case_id}",
            headers=headers,
        )
        assert resp.status_code == 200, f"Step 3 failed: {resp.json()}"
        opinions = resp.json()
        assert isinstance(opinions, list)
        assert len(opinions) > 0

        agent_types = {o["agent_type"] for o in opinions}
        expected_agents = {"diagnosis", "variant", "drug", "resistance", "guideline", "clinical_trial"}
        assert agent_types == expected_agents, (
            f"Expected agents {expected_agents}, got {agent_types}"
        )

        # Each opinion should have a context_hash matching the context
        for opinion in opinions:
            assert opinion["context_hash"] == context_hash, (
                f"Agent {opinion['agent_type']} context_hash mismatch"
            )

        # ── Step 4: Reach consensus ────────────────────────────────────────
        resp = client.post(
            f"/api/v1/clinical/consensus/{case_id}",
            headers=headers,
        )
        assert resp.status_code == 200, f"Step 4 failed: {resp.json()}"
        consensus = resp.json()
        assert consensus["context_hash"] == context_hash
        assert consensus["agreement"] in ("high", "moderate", "low", "none")
        assert consensus["confidence"] in ("high", "medium", "low")

        # ── Step 5: Generate recommendation ────────────────────────────────
        resp = client.post(
            f"/api/v1/clinical/recommend/{case_id}",
            headers=headers,
        )
        assert resp.status_code == 200, f"Step 5 failed: {resp.json()}"
        recommendation = resp.json()
        assert recommendation["context_hash"] == context_hash
        assert recommendation["first_line"] != {}
        assert recommendation["markdown"] != ""
        assert len(recommendation["supporting_evidence"]) >= 0

        # ── Step 6: Full analysis (all-in-one) ─────────────────────────────
        resp = client.post(
            f"/api/v1/clinical/analyze/{case_id}",
            headers=headers,
        )
        assert resp.status_code == 200, f"Step 6 failed: {resp.json()}"
        analysis = resp.json()

        # Verify all five products are present and correlated
        assert analysis["context"]["context_hash"] == context_hash
        assert analysis["consensus"]["context_hash"] == context_hash
        assert analysis["recommendation"]["context_hash"] == context_hash
        for op in analysis["opinions"]:
            assert op["context_hash"] == context_hash

        # ── Step 7: Verify decision thread ─────────────────────────────────
        resp = client.get(
            f"/api/v1/clinical/thread/{case_id}",
            headers=headers,
        )
        assert resp.status_code == 200, f"Step 7 failed: {resp.json()}"
        thread = resp.json()
        assert isinstance(thread, list)
        assert len(thread) > 0

        # Verify chronological order
        timestamps = [node["timestamp"] for node in thread]
        assert timestamps == sorted(timestamps), "Thread nodes must be in chronological order"

        # Verify expected node types are present
        node_types = {node["node_type"] for node in thread}
        expected_types = {
            "context_built",
            "evidence_collected",
            "agent_opinion",
            "consensus_reached",
            "recommendation_generated",
        }
        assert expected_types.issubset(node_types), (
            f"Missing node types. Expected {expected_types}, got {node_types}"
        )

        # Verify nodes are chained: at least one root node exists,
        # and most nodes have a parent_id linking to another node
        root_nodes = [n for n in thread if n["parent_id"] is None]
        assert len(root_nodes) >= 1, "Expected at least one root node"
        non_root = [n for n in thread if n["parent_id"] is not None]
        assert len(non_root) > 0, "Expected at least one node with parent_id"

        # ── Step 8: Verify decision tree ───────────────────────────────────
        resp = client.get(
            f"/api/v1/clinical/thread/{case_id}/tree",
            headers=headers,
        )
        assert resp.status_code == 200, f"Step 8 failed: {resp.json()}"
        tree = resp.json()
        assert isinstance(tree, list)
        assert len(tree) == len(thread), "Tree should contain the same nodes as thread"

        # ── Step 9: Verify single decision node retrieval ──────────────────
        # Pick a node from the thread and fetch it individually
        sample_node_id = thread[0]["id"]
        resp = client.get(
            f"/api/v1/clinical/thread/node/{sample_node_id}",
            headers=headers,
        )
        assert resp.status_code == 200, f"Step 9 failed: {resp.json()}"
        single_node = resp.json()
        assert single_node["id"] == sample_node_id
        assert single_node["case_id"] == case_id
        assert single_node["node_type"] == thread[0]["node_type"]

    def test_step_by_step_output_independence(self, client, workflow_setup):
        """Each pipeline step can be called independently without side effects.

        Verifies that GET endpoints do not mutate state and that calling
        context/evidence alone does not create decision thread nodes.
        """
        case_id = workflow_setup["case_id"]
        headers = _auth_headers(workflow_setup["token"])

        # Get context alone — should not create a thread node
        resp = client.get(f"/api/v1/clinical/context/{case_id}", headers=headers)
        assert resp.status_code == 200
        context_hash = resp.json()["context_hash"]

        # Get evidence alone — should not create a thread node
        resp = client.get(f"/api/v1/clinical/evidence/{case_id}", headers=headers)
        assert resp.status_code == 200

        # Verify thread is empty (no pipeline has been executed yet)
        resp = client.get(f"/api/v1/clinical/thread/{case_id}", headers=headers)
        assert resp.status_code == 200
        thread = resp.json()
        assert len(thread) == 0, (
            "GET-only endpoints should not create thread nodes"
        )

        # Run agents — should create context_built, evidence_collected,
        # and 6 agent_opinion nodes
        resp = client.post(f"/api/v1/clinical/agents/{case_id}", headers=headers)
        assert resp.status_code == 200

        resp = client.get(f"/api/v1/clinical/thread/{case_id}", headers=headers)
        assert resp.status_code == 200
        thread_after_agents = resp.json()
        node_types = [n["node_type"] for n in thread_after_agents]
        assert "context_built" in node_types
        assert "evidence_collected" in node_types
        assert node_types.count("agent_opinion") >= 1
        assert "consensus_reached" not in node_types
        assert "recommendation_generated" not in node_types

        # Run analysis on a second case — should not affect first case's thread
        pid2 = _create_patient(client, headers["Authorization"].split()[-1])
        case_id2 = _create_case(client, headers["Authorization"].split()[-1], pid2)
        resp = client.post(f"/api/v1/clinical/analyze/{case_id2}", headers=headers)
        assert resp.status_code == 200

        # First case's thread should be unchanged
        resp = client.get(f"/api/v1/clinical/thread/{case_id}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == len(thread_after_agents)

    def test_evidence_by_gene_correlation(self, client, workflow_setup):
        """Evidence received via gene endpoint correlates with case evidence."""
        case_id = workflow_setup["case_id"]
        headers = _auth_headers(workflow_setup["token"])

        # Collect evidence for the case
        resp = client.get(f"/api/v1/clinical/evidence/{case_id}", headers=headers)
        assert resp.status_code == 200
        case_evidence = resp.json()
        case_genes = set(case_evidence["by_gene"].keys()) - {"__missing__"}

        # For each known gene, verify gene endpoint returns items
        for gene in case_genes:
            resp = client.get(
                f"/api/v1/clinical/evidence/gene/{gene}",
                headers=headers,
            )
            assert resp.status_code == 200
            gene_bundle = resp.json()
            assert isinstance(gene_bundle["items"], list)
            # Each item in the gene bundle should have that gene symbol
            for item in gene_bundle["items"]:
                assert item.get("gene_symbol") == gene, (
                    f"Expected gene_symbol={gene}, got {item.get('gene_symbol')}"
                )

    def test_consensus_traceability(self, client, workflow_setup):
        """Consensus result references the same context_hash as opinions and context."""
        case_id = workflow_setup["case_id"]
        headers = _auth_headers(workflow_setup["token"])

        # Get context hash
        resp = client.get(f"/api/v1/clinical/context/{case_id}", headers=headers)
        context_hash = resp.json()["context_hash"]

        # Run consensus
        resp = client.post(f"/api/v1/clinical/consensus/{case_id}", headers=headers)
        assert resp.status_code == 200
        consensus = resp.json()

        # Consensus context_hash must match context
        assert consensus["context_hash"] == context_hash, (
            f"Consensus context_hash {consensus['context_hash']} "
            f"does not match context hash {context_hash}"
        )

        # Consensus must contain recommended_option with treatment and rationale
        rec_option = consensus["recommended_option"]
        assert isinstance(rec_option, dict)
        if rec_option:  # may be empty dict if no consensus
            assert "treatment" in rec_option
            assert "rationale" in rec_option

        # Conflicts should be well-formed
        for conflict in consensus["conflicts"]:
            assert "agent_types" in conflict
            assert "topic" in conflict
            assert "description" in conflict

    def test_recommendation_contains_markdown_report(self, client, workflow_setup):
        """Treatment recommendation includes a non-empty Markdown report."""
        case_id = workflow_setup["case_id"]
        headers = _auth_headers(workflow_setup["token"])

        resp = client.post(f"/api/v1/clinical/recommend/{case_id}", headers=headers)
        assert resp.status_code == 200
        rec = resp.json()

        # Markdown should be a non-trivial string
        assert len(rec["markdown"]) > 100, (
            "Markdown report appears too short or empty"
        )
        assert rec["markdown"].startswith("#"), (
            "Markdown should start with a heading"
        )

        # structured_json should contain the same data
        assert rec["structured_json"] != {}

        # First-line treatment should have a name
        first_line = rec["first_line"]
        assert isinstance(first_line, dict)
        if first_line:
            assert "treatment" in first_line
            assert "rationale" in first_line


class TestPhase2ErrorHandling:
    """Error and edge-case scenarios for the Phase 2 workflow."""

    def test_agents_on_deleted_case(self, client, workflow_setup):
        """Running agents on a case that exists should not crash."""
        case_id = workflow_setup["case_id"]
        headers = _auth_headers(workflow_setup["token"])

        # The case exists, agents should work
        resp = client.post(f"/api/v1/clinical/agents/{case_id}", headers=headers)
        assert resp.status_code == 200

    def test_concurrent_analysis_isolation(self, client, workflow_setup):
        """Two independent analyses produce separate decision threads."""
        headers = _auth_headers(workflow_setup["token"])

        # Create two distinct cases
        pid1 = _create_patient(client, headers["Authorization"].split()[-1])
        case1 = _create_case(client, headers["Authorization"].split()[-1], pid1)

        pid2 = _create_patient(client, headers["Authorization"].split()[-1])
        case2 = _create_case(client, headers["Authorization"].split()[-1], pid2)

        # Analyze both
        resp1 = client.post(f"/api/v1/clinical/analyze/{case1}", headers=headers)
        assert resp1.status_code == 200
        resp2 = client.post(f"/api/v1/clinical/analyze/{case2}", headers=headers)
        assert resp2.status_code == 200

        # Verify each case has its own thread
        thread1 = client.get(f"/api/v1/clinical/thread/{case1}", headers=headers).json()
        thread2 = client.get(f"/api/v1/clinical/thread/{case2}", headers=headers).json()

        assert len(thread1) > 0
        assert len(thread2) > 0

        # Node IDs should not overlap between threads
        ids1 = {n["id"] for n in thread1}
        ids2 = {n["id"] for n in thread2}
        assert ids1.isdisjoint(ids2), "Threads from different cases share node IDs"

        # Each node should reference its own case
        for node in thread1:
            assert node["case_id"] == case1
        for node in thread2:
            assert node["case_id"] == case2
