"""Product identity shared with the frontend; not a deployment record."""
import json
from pathlib import Path


VERSION = json.loads(
    (Path(__file__).resolve().parent / "frontend" / "src" / "productVersion.json")
    .read_text(encoding="utf-8")
)["version"]
