"""Bundled synthetic demo dataset support for AI-Kill-Cancer."""

from src.backend.demo.bootstrap import bootstrap_demo_dataset
from src.backend.demo.maintenance import rebuild_demo_dataset, reset_demo_dataset

__all__ = ["bootstrap_demo_dataset", "reset_demo_dataset", "rebuild_demo_dataset"]
