from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

def save_json(path: str, payload: Dict[str, Any]) -> str:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(file_path.resolve())

def load_json(path: str) -> Optional[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return None
    return json.loads(file_path.read_text(encoding="utf-8"))
