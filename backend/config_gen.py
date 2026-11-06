import os
import tempfile
import yaml
from pathlib import Path


def generate_config(job_dir: Path, form_data: dict) -> Path:
    """
    Build a patient-specific config.yaml from intake form data.
    form_data keys: cancer_type, hla_alleles (list), data_mode,
                    gcs_variants, gcs_scrna, patient_name
    """
    workdir = str(job_dir)
    data_dir = str(job_dir / "data")
    results_dir = str(job_dir / "results")

    raw_hla = form_data.get("hla_alleles")
    hla_alleles = raw_hla if isinstance(raw_hla, list) and raw_hla else [
        "HLA-A*02:01", "HLA-B*07:02", "HLA-C*07:02"
    ]

    # Data source: either uploaded files (local) or GCS paths from form
    data_mode = form_data.get("data_mode", "upload")
    if data_mode == "gcs":
        variants_bucket = form_data.get("gcs_variants", "")
        scrna_bucket = form_data.get("gcs_scrna", "")
    else:
        # Files were uploaded to job_dir/data/variants/ already
        variants_bucket = ""
        scrna_bucket = ""

    cfg = {
        "patient": {
            "name": form_data.get("patient_name", "unknown"),
            "cancer_type": form_data.get("cancer_type", "unknown"),
            "job_id": job_dir.name,
        },
        "paths": {
            "workdir": workdir,
            "data": data_dir,
            "results": results_dir,
            "reference": str(job_dir / "data" / "reference"),
        },
        "data_sources": {
            "variants_bucket": variants_bucket,
            "scrna_bucket": scrna_bucket,
            "neoantigen_bucket": "",
            "scrna_fallback_geo": "",
            "data_mode": data_mode,
        },
        "hla": {
            "class_i": hla_alleles,
        },
        "phase2_annotation": {
            "vep_assembly": "GRCh38",
            "vep_fork": 4,
        },
        "phase3_scrna": {
            "min_genes": 200,
            "min_cells": 3,
            "max_mt_pct": 20,
            "n_top_genes": 3000,
            "leiden_resolution": 0.8,
            "enabled": bool(form_data.get("has_scrna", False)),
            "target_genes": [
                "FAP", "CD276", "EPHA2", "MSLN", "FOLR1",
                "MUC1", "ERBB2", "EGFR", "MET", "PDGFRA", "KIT",
            ],
        },
        "phase4_neoantigens": {
            "binding_threshold": 500,
            "epitope_lengths": [8, 9, 10, 11],
            "predictors": ["MHCflurry"],
            "top_n_candidates": 50,
            "min_vaf": 0.05,
            "min_expression": 1.0,
        },
        "phase5_alphafold": {
            "use_esmfold_prescreen": True,
            "esmfold_api": "https://api.esmatlas.com/foldSequence/v1/pdb/",
            "use_colabfold_local": False,
            "use_modal": False,
            "iptm_threshold": 0.5,
            "pae_threshold": 10,
            "plddt_threshold": 85,
            "max_candidates_for_af": 20,
        },
        "phase6_treatment": {
            "template": "TREATMENT_RECOMMENDATION.md",
        },
    }

    config_path = job_dir / "config.yaml"
    tmp_path = config_path.with_suffix(".yaml.tmp")
    tmp_path.write_text(
        yaml.dump(cfg, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    os.replace(tmp_path, config_path)
    return config_path
