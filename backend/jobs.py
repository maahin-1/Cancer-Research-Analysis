import json
import os
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

_locks: dict[str, threading.Lock] = {}
_locks_mu = threading.Lock()


def _job_lock(job_id: str) -> threading.Lock:
    with _locks_mu:
        if job_id not in _locks:
            _locks[job_id] = threading.Lock()
        return _locks[job_id]

JOBS_DIR = Path(__file__).parent.parent / "jobs"


def create_job() -> str:
    job_id = str(uuid.uuid4())  # full UUID, no truncation
    job_dir = JOBS_DIR / job_id
    for sub in ["data/variants", "data/scrna", "results"]:
        (job_dir / sub).mkdir(parents=True, exist_ok=True)
    _write_status(job_id, {"phase": "created", "status": "pending",
                           "started_at": datetime.now().isoformat(),
                           "finished_at": None, "error": None})
    return job_id


def get_job(job_id: str) -> dict | None:
    status_path = JOBS_DIR / job_id / "status.json"
    if not status_path.exists():
        return None
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def update_job(job_id: str, **kwargs):
    with _job_lock(job_id):
        status = get_job(job_id) or {}
        status.update(kwargs)
        _write_status(job_id, status)


def job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def _write_status(job_id: str, data: dict):
    path = JOBS_DIR / job_id / "status.json"
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise
