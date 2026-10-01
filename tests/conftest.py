import pytest
from uuid import uuid4

from src.utils import namespace as namespace_module


@pytest.fixture(autouse=True)
def isolated_namespace(tmp_path, monkeypatch):
    """Every Edge() construction calls get_ns_uuid() unconditionally
    (see Edge._set_id in schemas.py), so tests need a valid namespace
    file without touching the project's real .pixidb/ directory."""
    namespace_file = tmp_path / "namespace.uuid"
    namespace_file.write_text(str(uuid4()), encoding="utf-8")
    monkeypatch.setattr(namespace_module, "NAMESPACE_FILE", str(namespace_file))
    yield
