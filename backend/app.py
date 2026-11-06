import csv
import json
import re
import sys
import aiofiles
from pathlib import PurePosixPath
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).parent))
import jobs
import config_gen
import runner

app = FastAPI(title="Cancer Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5500", "http://127.0.0.1:5500",
        "null",  # file:// origin used when opening HTML directly from disk
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _validate_job_id(job_id: str) -> None:
    if not _UUID_RE.match(job_id):
        raise HTTPException(status_code=400, detail="invalid job_id")


def _safe_filename(filename: str) -> str:
    """Strip any directory components so an uploaded filename can never
    escape its destination folder (e.g. '../../evil.txt' or an absolute
    path written by a malicious or buggy client)."""
    name = PurePosixPath(filename.replace("\\", "/")).name
    return name or "upload"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/submit")
async def submit(
    patient_name: str = Form(""),
    cancer_type: str = Form(""),
    hla_alleles: str = Form("[]"),      # JSON array string
    data_mode: str = Form("upload"),    # "upload" or "gcs"
    gcs_variants: str = Form(""),
    gcs_scrna: str = Form(""),
    has_scrna: str = Form("false"),
    vcf_file: UploadFile | None = File(None),
    scrna_file: UploadFile | None = File(None),
):
    # Validate HLA alleles JSON before creating the job
    try:
        parsed_hla = json.loads(hla_alleles)
        if not isinstance(parsed_hla, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        return JSONResponse({"error": "hla_alleles must be a JSON array"}, status_code=422)

    job_id = jobs.create_job()
    job_d = jobs.job_dir(job_id)

    # Save uploaded files in chunks to avoid loading large VCFs into RAM
    if vcf_file and vcf_file.filename:
        dest = job_d / "data" / "variants" / _safe_filename(vcf_file.filename)
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as f:
            while chunk := await vcf_file.read(1024 * 1024):
                await f.write(chunk)

    if scrna_file and scrna_file.filename:
        dest = job_d / "data" / "scrna" / _safe_filename(scrna_file.filename)
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as f:
            while chunk := await scrna_file.read(1024 * 1024):
                await f.write(chunk)

    form_data = {
        "patient_name": patient_name,
        "cancer_type": cancer_type,
        "hla_alleles": parsed_hla,
        "data_mode": data_mode,
        "gcs_variants": gcs_variants,
        "gcs_scrna": gcs_scrna,
        "has_scrna": has_scrna.lower() == "true",
    }
    config_path = config_gen.generate_config(job_d, form_data)
    runner.run_pipeline(job_id, config_path, jobs)

    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
async def status_stream(job_id: str):
    """Server-Sent Events stream: sends new log lines, then a 'done' event."""
    _validate_job_id(job_id)
    job_d = jobs.job_dir(job_id)
    log_path = job_d / "pipeline.log"

    async def event_generator():
        try:
            # Wait up to 5s for log file to appear
            for _ in range(50):
                if log_path.exists():
                    break
                await asyncio.sleep(0.1)

            sent = 0
            while True:
                status = jobs.get_job(job_id)
                if log_path.exists():
                    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                    for line in lines[sent:]:
                        yield f"data: {json.dumps({'type': 'log', 'text': line})}\n\n"
                    sent = len(lines)

                if status and status.get("status") in ("success", "error"):
                    # Flush any lines written at the same time as job completion
                    if log_path.exists():
                        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                        for line in lines[sent:]:
                            yield f"data: {json.dumps({'type': 'log', 'text': line})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'status': status})}\n\n"
                    break

                await asyncio.sleep(1)
        except asyncio.CancelledError:
            return  # client disconnected

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/results/{job_id}")
def get_results(job_id: str):
    _validate_job_id(job_id)
    job_d = jobs.job_dir(job_id)
    status = jobs.get_job(job_id)
    if not status:
        return JSONResponse({"error": "job not found"}, status_code=404)

    results: dict = {"status": status, "candidates": [], "treatment": "", "targets": []}

    candidates_csv = job_d / "results" / "FINAL_neoantigen_candidates_ranked.csv"
    if candidates_csv.exists():
        try:
            with open(candidates_csv, encoding="utf-8") as f:
                results["candidates"] = list(csv.DictReader(f))
        except Exception:
            results["candidates"] = []

    treatment_md = job_d / "results" / "TREATMENT_RECOMMENDATION.md"
    if treatment_md.exists():
        results["treatment"] = treatment_md.read_text(encoding="utf-8")

    targets_csv = job_d / "results" / "scrna" / "target_discovery_summary.csv"
    if targets_csv.exists():
        try:
            with open(targets_csv, encoding="utf-8") as f:
                results["targets"] = list(csv.DictReader(f))
        except Exception:
            results["targets"] = []

    return results
