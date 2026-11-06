import uuid

import pytest
from fastapi.testclient import TestClient

import app as app_module
import jobs


@pytest.fixture
def client():
    return TestClient(app_module.app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_submit_without_files_creates_a_job(client):
    resp = client.post("/api/submit", data={
        "patient_name": "test", "cancer_type": "osteosarcoma", "hla_alleles": "[]",
    })
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    uuid.UUID(job_id)
    assert jobs.get_job(job_id) is not None


def test_submit_rejects_malformed_hla_alleles_json(client):
    resp = client.post("/api/submit", data={
        "patient_name": "test", "hla_alleles": "not-json",
    })
    assert resp.status_code == 422


def test_submit_rejects_hla_alleles_that_is_not_a_list(client):
    resp = client.post("/api/submit", data={
        "patient_name": "test", "hla_alleles": '{"a": 1}',
    })
    assert resp.status_code == 422


def test_results_for_unknown_job_is_404(client):
    resp = client.get(f"/api/results/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_results_rejects_a_malformed_job_id(client):
    resp = client.get("/api/results/not-a-uuid")
    assert resp.status_code == 400


def test_status_stream_rejects_a_malformed_job_id(client):
    resp = client.get("/api/status/not-a-uuid")
    assert resp.status_code == 400


def test_uploaded_filename_cannot_escape_the_job_directory(client, tmp_path):
    # Regression test for a real path-traversal bug: vcf_file.filename was
    # used verbatim to build the destination path, so a filename like
    # "../../../evil.txt" would write outside the job's own folder (and
    # outside jobs/ entirely). app._safe_filename() now strips any
    # directory components before the path is built.
    malicious_name = "../../../evil.txt"
    files = {"vcf_file": (malicious_name, b"payload", "text/plain")}
    data = {"patient_name": "t", "cancer_type": "t", "hla_alleles": "[]", "data_mode": "upload"}
    resp = client.post("/api/submit", data=data, files=files)
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    job_d = jobs.job_dir(job_id)

    # The file must land inside job_d/data/variants, never above it.
    variants_dir = job_d / "data" / "variants"
    written = list(variants_dir.iterdir())
    assert len(written) == 1
    assert written[0].parent == variants_dir
    assert written[0].read_bytes() == b"payload"

    # And it must NOT have escaped anywhere above the jobs directory.
    escaped_path = (job_d / ".." / ".." / ".." / "evil.txt").resolve()
    assert not escaped_path.exists()


def test_uploaded_filename_with_absolute_path_is_sanitized(client):
    malicious_name = "/etc/evil.txt"
    files = {"vcf_file": (malicious_name, b"payload", "text/plain")}
    data = {"patient_name": "t", "cancer_type": "t", "hla_alleles": "[]", "data_mode": "upload"}
    resp = client.post("/api/submit", data=data, files=files)
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    variants_dir = jobs.job_dir(job_id) / "data" / "variants"
    written = list(variants_dir.iterdir())
    assert len(written) == 1
    assert written[0].name == "evil.txt"
