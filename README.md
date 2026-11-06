# Founder Mode on Cancer: open research on personalized cancer treatment, neoantigen pipeline and AI agent skill

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Skill](https://img.shields.io/badge/agent%20skill-founder--mode--oncology-blue)
![Tests](https://img.shields.io/badge/tests-18%20passing-brightgreen)

**This repository is an open research compilation on personalized cancer treatment, based on how Sid Sijbrandij (GitLab co-founder) applied "founder mode" thinking to his own osteosarcoma care.** It contains 14 research documents (timeline, diagnostics, treatments, MRD tracking, systemic barriers, the role of AI), an AlphaFold integration layer, a public cancer-genomics dataset catalog, a 6-phase end-to-end test plan, an installable AI agent skill, and a local web dashboard with a FastAPI job runner for a personalized oncology pipeline.

**This is research and education, not medical advice.** Nothing here replaces a clinician. Discuss any treatment decision with a qualified oncologist.

---

## Contents

- [Background](#background)
- [What This Repo Contains](#what-this-repo-contains)
- [Proof that it runs](#proof-that-it-runs)
- [Quick Install (Agent Skill)](#quick-install-agent-skill)
- [Key Data Sources](#key-data-sources)
- [Test Plan](#test-plan)
- [Key Sources](#key-sources)
- [Blog Post](#blog-post)
- [Why This Matters](#why-this-matters)
- [Honest status](#honest-status)
- [FAQ](#faq)
- [License](#license)

---

## Background

In November 2022, Sid Sijbrandij was diagnosed with osteosarcoma — a rare bone cancer — in his T5 vertebra. After standard-of-care treatment and a 2024 recurrence, he applied "founder mode" thinking to his own healthcare: maximal diagnostics, parallel (not sequential) treatments, and personalized therapeutic development.

His cancer is now undetectable. Tumor-infiltrating T cells went from **19% to 89%**. His **25 TB** of genomic data is publicly available on Google Cloud.

## What This Repo Contains

### Research (14 files)

| File | Description |
|------|-------------|
| [overview.md](overview.md) | Case summary — diagnosis, standard care, founder mode pivot, outcome |
| [framework.md](framework.md) | Three-pillar decision framework (diagnostics, therapeutics, parallel treatment) |
| [timeline.md](timeline.md) | Complete chronological record (Nov 2022 - Mar 2026) — every scan, biopsy, drug |
| [diagnostics.md](diagnostics.md) | All diagnostic modalities: WGS, WES, scRNA-seq, ctDNA x3, organoids, PET tracers |
| [treatments.md](treatments.md) | Full catalog: chemo, checkpoint inhibitors, vaccines (5 versions), radioligand, gene therapy |
| [mrd-tracking.md](mrd-tracking.md) | Liquid biopsy data from 3 platforms with cross-platform comparison |
| [breakthroughs.md](breakthroughs.md) | 7 key turning points — scRNA-seq revealing FAP, immune shift 19%→89% |
| [systemic-barriers.md](systemic-barriers.md) | 7 systemic barriers: tissue access, IRBs, data portability, economics |
| [ai-role.md](ai-role.md) | How ChatGPT was used: literature review, decision support, balanced scorecards |
| [future-vision.md](future-vision.md) | Scaling vision: Even One Ventures, platform technologies, projected $175K cost |
| [open-data.md](open-data.md) | 25TB open dataset on Google Cloud, osteosarc.com portal |
| [secondary-conditions.md](secondary-conditions.md) | Complications: hip AVN, thyroid dysfunction, spinal infection |
| [resources.md](resources.md) | All links, people, institutions, technologies, statistics |
| [source-code.md](source-code.md) | Open-source toolchain: openvax, pVACtools, openvaxx, GATK, Scanpy |

### AlphaFold Integration

| File | Description |
|------|-------------|
| [alphafold-integration.md](alphafold-integration.md) | 4 structural biology workflows: neoantigen-MHC validation, radioligand modeling, de novo binder design, mutation impact analysis |

### Test Infrastructure

| File | Description |
|------|-------------|
| [public-datasets.md](public-datasets.md) | 461-line catalog of every open cancer genomics source (osteosarc.com GCS paths, TCGA, GEO, cBioPortal, IEDB/CEDAR, PDB, SEQC2) |
| [test-plan.md](test-plan.md) | 6-phase end-to-end pipeline test using Sid's actual data from `gs://osteosarc-genomics` |

### Packaged Skill

| File | Description |
|------|-------------|
| [founder-mode-oncology.skill](founder-mode-oncology.skill) | Packaged agent skill (zip) — installable across 37+ AI agents |

### Dashboard and local pipeline runner

| Path | Description |
|------|-------------|
| `dashboard/` | Landing page, patient intake form and report page (static HTML) |
| `backend/` | FastAPI service with `/api/health`, `/api/submit`, `/api/status/{job_id}` and `/api/results/{job_id}`; runs `egri/founder-mode-pipeline/scripts/pipeline.py` as a background job and tracks progress in `status.json` |
| `results/` | Example pipeline outputs: ranked neoantigen candidates, scRNA and AlphaFold results, and a treatment recommendation file |

Run the backend on Windows with `backend/start.bat`, which creates a virtual environment and installs `backend/requirements.txt`.

---

## Proof that it runs

Everything below was run on **Python 3.11.15, Windows 11**, in a fresh virtual environment built from `backend/requirements.txt` plus `pytest` and `httpx`.

```text
$ cd backend && python -m pytest tests/ -q
..................                                                        [100%]
18 passed in ~1s
```

The FastAPI backend was also started for real with `uvicorn app:app` and exercised with live HTTP requests (`/api/health`, `/api/submit`), not just the test client — both returned correct responses against a real running server.

One real, serious bug was found and fixed in the process:

- **Path traversal in file upload (`/api/submit`).** `vcf_file.filename` and `scrna_file.filename` — client-controlled values — were used verbatim to build the destination path on disk: `job_d / "data" / "variants" / vcf_file.filename`. A filename like `"../../../../evil.txt"` walked straight out of the job directory and the `jobs/` folder entirely, writing the uploaded file's contents anywhere on the filesystem the server process could reach. Confirmed by actually sending that filename to a live instance of the endpoint — the file landed outside the repo root. Fixed in `backend/app.py` by adding `_safe_filename()`, which strips every directory component (via `PurePosixPath(...).name`) before the path is built, so an uploaded file can never land anywhere but its intended folder. Covered by `backend/tests/test_app.py::test_uploaded_filename_cannot_escape_the_job_directory` and `::test_uploaded_filename_with_absolute_path_is_sanitized`.

The `egri/founder-mode-pipeline/scripts/` pipeline itself (VEP annotation, Scanpy scRNA-seq, pVACseq/MHCflurry neoantigen calling, AlphaFold/ESMFold structural validation) was **not** run end-to-end — by its own [test-plan.md](test-plan.md), that requires ~24–48h of wall clock, cloud GPU access, and bioinformatics tools (VEP, Scanpy, pVACtools) that aren't installable in this environment. The files in `results/` are the project's own pre-existing example output, not something regenerated here.

---

## Quick Install (Agent Skill)

```bash
npx skills add broomva/founder-mode-oncology
```

The skill packages the entire framework into 7 files (1,321 lines) with decision workflows, open-source pipeline references, regulatory navigation, MRD monitoring interpretation, and AlphaFold/RFdiffusion structural biology integration.

Skill repo: [github.com/broomva/founder-mode-oncology](https://github.com/broomva/founder-mode-oncology)

## Key Data Sources

| Source | URL | Access | Highlight |
|--------|-----|--------|-----------|
| osteosarc.com | [osteosarc.com](https://osteosarc.com) | Public GCS bucket | 24.88 TiB — WGS, WES, scRNA-seq, pre-called VCFs, HLA typing |
| GEO osteosarcoma | [GSE152048](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE152048) | Direct download | 100K osteosarcoma single cells |
| TCGA | [portal.gdc.cancer.gov](https://portal.gdc.cancer.gov/) | Open MAFs, no login | 33 cancer types, 11K+ patients |
| CEDAR | [cedar.iedb.org](https://cedar.iedb.org/) | Free | 224K+ cancer epitopes |
| PDB (FAP) | [1Z68](https://www.rcsb.org/structure/1Z68) | Direct download | Crystal structure of FAP at 2.0 A |
| AlphaFold DB | [AF-Q12884-F1](https://alphafold.ebi.ac.uk/entry/Q12884) | Direct download | Predicted FAP structure |

See [public-datasets.md](public-datasets.md) for the complete catalog (30+ sources).

## Test Plan

The [test-plan.md](test-plan.md) defines a 6-phase pipeline test on Sid's actual data:

1. **Acquire** — Download pre-called VCFs + RNA-seq + scRNA-seq from `gs://osteosarc-genomics` (~20 GB)
2. **Annotate** — VEP annotation for pVACseq compatibility
3. **scRNA-seq** — Scanpy target discovery (confirm FAP, identify additional targets)
4. **Neoantigens** — pVACseq + MHCflurry + Vaxrank → top 50 candidates
5. **AlphaFold** — Multimer validation of peptide-MHC complexes (Modal A100)
6. **Treatment** — Full parallel combination recommendation using skill's decision workflow

**Budget**: ~24-48h wall clock, ~$5-15 cloud GPU. Zero approvals needed.

## Key Sources

- [sytse.com/cancer](https://sytse.com/cancer/) — Hub page
- [osteosarc.com](https://osteosarc.com) — Open data portal (25TB genomic/imaging data)
- [Century of Bio: Going Founder Mode on Cancer](https://centuryofbio.com/p/sid) — Elliot Hershberg's deep-dive article
- [Even One Ventures](https://evenone.ventures) — Venture fund scaling this approach
- [sijbrandij.substack.com](https://sijbrandij.substack.com) — Sid's newsletter
- OpenAI Forum: "Terminal to Turnaround: How GitLab's Co-Founder Leveraged ChatGPT in His Cancer Fight"

## Blog Post

Published on broomva.tech: [Founder Mode on Cancer: From Terminal Diagnosis to Open-Source Cure](https://broomva.tech/writing/founder-mode-cancer)

## Why This Matters

> "It costs $1B to get a drug approved. But it costs $1M to dose a single person with personalized therapy." — Sid Sijbrandij

The technologies for personalized cancer treatment exist today. The barriers are systemic: regulatory friction, hospital tissue-access policies, data portability, and business models optimized for blockbuster drugs over individualized medicine.

---

## Honest status

- **Research and education only, not medical advice or a clinical tool.** Nothing here has been validated for clinical use.
- **The FastAPI backend, intake dashboard and job-tracking layer are real, tested code** — verified above by actually running it and starting a live server.
- **The bioinformatics pipeline it kicks off is not independently verified here.** Running it for real needs cloud GPU access and several heavy, non-trivial-to-install tools (VEP, Scanpy, pVACtools); the `results/` directory holds the project's own pre-existing example output, not output regenerated during this review.
- **The research documents are a compilation**, not primary clinical data generated by this project.
- **Verified on one setup:** Python 3.11 on Windows, backend only.

---

## FAQ

### What is Founder Mode on Cancer?
A compilation of research, data catalogs, a test plan and tooling that documents and generalises a founder-style, data-driven approach to personalized cancer treatment.

### Is this medical advice?
No. It is research and educational material. Talk to a qualified oncologist before making any treatment decision.

### What is in the repository?
Research documents, AlphaFold workflows, a catalog of public cancer genomics data, a 6-phase test plan, results files, a packaged agent skill, and a dashboard with a FastAPI backend.

### How do I install the agent skill?
Run `npx skills add broomva/founder-mode-oncology`. It packages the framework into seven files for use across many AI agents.

### Where does the underlying data come from?
Sid Sijbrandij's publicly released 25 TB genomic dataset on Google Cloud, plus public sources such as TCGA, GEO, cBioPortal, IEDB and PDB.

### Is the backend actually tested?
Yes — 18 tests cover job creation/status, config generation and the FastAPI endpoints, including a regression test for a real path-traversal bug found and fixed in the file-upload handler. See [Proof that it runs](#proof-that-it-runs).

### Who wrote it?
Maahin Bir Singh Osahan.

## License

MIT. See [LICENSE](LICENSE).
