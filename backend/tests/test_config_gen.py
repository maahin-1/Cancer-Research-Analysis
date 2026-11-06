import yaml

import jobs
import config_gen


def test_generate_config_writes_valid_yaml_with_defaults():
    job_id = jobs.create_job()
    job_d = jobs.job_dir(job_id)
    config_path = config_gen.generate_config(job_d, {})
    assert config_path.exists()
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert cfg["hla"]["class_i"] == ["HLA-A*02:01", "HLA-B*07:02", "HLA-C*07:02"]
    assert cfg["patient"]["name"] == "unknown"
    assert cfg["phase3_scrna"]["enabled"] is False


def test_generate_config_uses_provided_hla_alleles():
    job_id = jobs.create_job()
    job_d = jobs.job_dir(job_id)
    config_path = config_gen.generate_config(job_d, {"hla_alleles": ["HLA-A*01:01"]})
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert cfg["hla"]["class_i"] == ["HLA-A*01:01"]


def test_generate_config_gcs_mode_fills_bucket_paths():
    job_id = jobs.create_job()
    job_d = jobs.job_dir(job_id)
    config_path = config_gen.generate_config(job_d, {
        "data_mode": "gcs",
        "gcs_variants": "gs://bucket/variants",
        "gcs_scrna": "gs://bucket/scrna",
    })
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert cfg["data_sources"]["variants_bucket"] == "gs://bucket/variants"
    assert cfg["data_sources"]["scrna_bucket"] == "gs://bucket/scrna"


def test_generate_config_upload_mode_leaves_bucket_paths_empty():
    job_id = jobs.create_job()
    job_d = jobs.job_dir(job_id)
    config_path = config_gen.generate_config(job_d, {
        "data_mode": "upload",
        "gcs_variants": "gs://should-be-ignored",
    })
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert cfg["data_sources"]["variants_bucket"] == ""
