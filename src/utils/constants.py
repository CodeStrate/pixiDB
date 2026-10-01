from dotenv import load_dotenv
import os
load_dotenv()

PIXIDB_DIR = os.getenv("PIXIDB_DIR", ".pixidb")
NAMESPACE_FILE = f"{PIXIDB_DIR}/namespace.uuid"