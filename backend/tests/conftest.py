import sys
import shutil
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import jobs  # noqa: E402
import runner  # noqa: E402


@pytest.fixture(autouse=True)
def no_real_pipeline_subprocess(monkeypatch):
    """app.submit() launches the real (heavy, cloud-dependent) pipeline as a
    background subprocess. Tests only need to exercise the HTTP/validation
    layer, so replace it with a no-op — otherwise every submit test spawns a
    real subprocess thread that outlives the test and the tmp_path it was
    writing into, into an interleaved FileNotFoundError once pytest cleans
    the directory up."""
    monkeypatch.setattr(runner, "run_pipeline", lambda *a, **kw: None)


@pytest.fixture(autouse=True)
def isolated_jobs_dir(tmp_path, monkeypatch):
    """Redirect jobs.JOBS_DIR to a throwaway temp folder for every test, so
    tests never touch the repo's real jobs/ directory and never leak files
    outside it even if a test is probing for a path-traversal bug."""
    fake_jobs_dir = tmp_path / "jobs"
    fake_jobs_dir.mkdir()
    monkeypatch.setattr(jobs, "JOBS_DIR", fake_jobs_dir)
    yield fake_jobs_dir
    shutil.rmtree(fake_jobs_dir, ignore_errors=True)
