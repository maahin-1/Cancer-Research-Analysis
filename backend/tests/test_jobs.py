import uuid

import jobs


def test_create_job_returns_a_valid_uuid_and_makes_the_expected_dirs():
    job_id = jobs.create_job()
    uuid.UUID(job_id)  # raises if not a valid UUID
    job_d = jobs.job_dir(job_id)
    assert (job_d / "data" / "variants").is_dir()
    assert (job_d / "data" / "scrna").is_dir()
    assert (job_d / "results").is_dir()


def test_create_job_writes_a_pending_status():
    job_id = jobs.create_job()
    status = jobs.get_job(job_id)
    assert status["status"] == "pending"
    assert status["phase"] == "created"
    assert status["finished_at"] is None


def test_get_job_returns_none_for_unknown_job():
    assert jobs.get_job(str(uuid.uuid4())) is None


def test_update_job_merges_fields_without_dropping_existing_ones():
    job_id = jobs.create_job()
    jobs.update_job(job_id, status="running", phase="running")
    status = jobs.get_job(job_id)
    assert status["status"] == "running"
    assert status["phase"] == "running"
    assert "started_at" in status  # original field preserved


def test_update_job_survives_concurrent_writers():
    import threading

    job_id = jobs.create_job()

    def bump(i):
        jobs.update_job(job_id, counter=i)

    threads = [threading.Thread(target=bump, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No crash, and the status file is still valid JSON with some counter value
    status = jobs.get_job(job_id)
    assert "counter" in status
