"""
Adapters package — third-party data source integration interfaces.
"""
from src.backend.adapters.base import AdapterResult, BaseAdapter, NotConfiguredAdapter  # noqa: F401
from src.backend.adapters.registry import AdapterRegistry, get_registry  # noqa: F401
