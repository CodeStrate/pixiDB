from uuid import uuid4
import os
from src.utils.constants import PIXIDB_DIR, NAMESPACE_FILE

class GraphEngine:
    def __init__(self):
        self._generate_namespace_uuid()
    
    def _generate_namespace_uuid(self):
        os.makedirs(PIXIDB_DIR, exist_ok=True)
        if os.path.exists(NAMESPACE_FILE):
            return
        
        namespace = uuid4()
        with open(NAMESPACE_FILE, "w+") as f:
            f.write(str(namespace))

        f.close()