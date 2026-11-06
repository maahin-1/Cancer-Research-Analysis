import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

PIPELINE_SCRIPT = (
    Path(__file__).parent.parent
    / "egri" / "founder-mode-pipeline" / "scripts" / "pipeline.py"
)


def run_pipeline(job_id: str, config_path: Path, jobs_module) -> None:
    """
    Launch pipeline.py as a subprocess in a background thread.
    Writes stdout+stderr to job_dir/pipeline.log.
    Updates status.json at start and finish.
    """
    job_d = jobs_module.job_dir(job_id)
    log_path = job_d / "pipeline.log"

    def _run():
        try:
            jobs_module.update_job(job_id, phase="running", status="running")
            with open(log_path, "w", encoding="utf-8") as log_f:
                proc = subprocess.Popen(
                    [sys.executable, str(PIPELINE_SCRIPT), str(config_path)],
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    cwd=str(job_d),
                    text=True,
                )
                proc.wait()

            if proc.returncode == 0:
                jobs_module.update_job(
                    job_id,
                    phase="complete",
                    status="success",
                    finished_at=datetime.now().isoformat(),
                )
            else:
                jobs_module.update_job(
                    job_id,
                    phase="error",
                    status="error",
                    error=f"Pipeline exited with code {proc.returncode}",
                    finished_at=datetime.now().isoformat(),
                )
        except Exception as exc:
            jobs_module.update_job(
                job_id,
                phase="error",
                status="error",
                error=str(exc),
                finished_at=datetime.now().isoformat(),
            )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
