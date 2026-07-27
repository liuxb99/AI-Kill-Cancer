"""Phase 3D — Graph Rebuild Tests."""



class TestRebuildCLI:
    """重建功能测试。"""

    def test_cli_import(self):
        """CLI 模块可导入。"""
        from src.backend.cli.clinical_graph import main, rebuild

        assert main is not None
        assert rebuild is not None

    def test_retry_policy_import(self):
        """重试策略可导入。"""
        from src.backend.clinical_graph.retry_policy import DEFAULT_RETRY_POLICY, GraphProjectionRetryPolicy

        assert DEFAULT_RETRY_POLICY is not None
        assert GraphProjectionRetryPolicy is not None

    def test_worker_import(self):
        """Worker 可导入。"""
        from src.backend.clinical_graph.worker import ClinicalGraphProjectionWorker

        assert ClinicalGraphProjectionWorker is not None

    def test_client_import(self):
        """Client 可导入。"""
        from src.backend.clinical_graph.client import ClinicalGraphClient

        assert ClinicalGraphClient is not None
