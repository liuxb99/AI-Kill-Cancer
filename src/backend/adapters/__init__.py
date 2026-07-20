"""
Adapters package — third-party data source integration interfaces.
"""
from src.backend.adapters.base import BaseAdapter, NotConfiguredAdapter, AdapterResult
from src.backend.adapters.registry import AdapterRegistry, get_registry
