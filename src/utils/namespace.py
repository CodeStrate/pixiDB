import os
import warnings
from uuid import UUID
from src.utils.constants import NAMESPACE_FILE

def get_ns_uuid():
    if not os.path.exists(NAMESPACE_FILE):
        raise RuntimeError("Namespace not initialized. Please initialize it first.")
    with open(NAMESPACE_FILE, "r", encoding="utf-8") as f:
        uuid = f.read()
        return UUID(uuid)