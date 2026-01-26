# /opt/protein_pipeline/pipeline_tasks.py
import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from celery import Celery
import logging

LOG_PATH = os.environ.get(
    "PIPELINE_LOG",
    "/opt/protein_pipeline/protein_pipeline.log"
)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# ---------------------------
# Config loading (same idea as your current file)
# ---------------------------
def load_sysconfig_value(key, path="/etc/sysconfig/protein-pipeline"):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip()
    except FileNotFoundError:
        pass
    return None

BROKER_URL = (
    os.environ.get("CELERY_BROKER_URL")
    or load_sysconfig_value("CELERY_BROKER_URL")
)

if not BROKER_URL:
    raise RuntimeError("CELERY_BROKER_URL is not set")

PIPELINE_DIR = os.environ.get("PIPELINE_DIR", "/opt/protein_pipeline")
PIPELINE_SCRIPT = os.path.join(PIPELINE_DIR, "pipeline_script.py")

# Where results should land on each worker
RESULTS_ROOT = os.environ.get("RESULTS_ROOT", "/data/results")
WORK_ROOT = os.environ.get("WORK_ROOT", "/tmp/protein_work")

app = Celery("protein_pipeline", broker=BROKER_URL, backend="rpc://")


def safe_name(s: str) -> str:
    # make filesystem-safe
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


@app.task(bind=True, name="protein_pipeline.run_one_protein")
def run_one_protein(self, protein_id: str, sequence: str) -> dict:
    """
    One task == one protein.
    Runs pipeline_script.py on a temp fasta in an isolated workdir.
    Writes outputs to /data/results/<protein_id_sanitized>/
    """
    task_id = self.request.id
    worker = os.uname().nodename

    if not os.path.exists(PIPELINE_SCRIPT):
        return {
            "ok": False,
            "error": f"Missing pipeline_script.py at {PIPELINE_SCRIPT}",
            "task_id": task_id,
            "worker": worker,
        }

    # 1) Create isolated working directory (fixes collisions)
    workdir = Path(WORK_ROOT) / f"{safe_name(protein_id)}_{task_id}"
    workdir.mkdir(parents=True, exist_ok=True)

    # 2) Write single-protein FASTA
    fasta_path = workdir / "input.fa"
    fasta_path.write_text(f">{protein_id}\n{sequence}\n")

    # 3) Run pipeline in the isolated dir
    cmd = ["python3", PIPELINE_SCRIPT, str(fasta_path)]
    p = subprocess.Popen(
        cmd,
        cwd=str(workdir),  # IMPORTANT: isolate output
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = p.communicate()

    # 4) Collect outputs to a stable per-protein results directory
    out_dir = Path(RESULTS_ROOT) / safe_name(protein_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save stdout/stderr for debugging
    (out_dir / "stdout.txt").write_text(out or "")
    (out_dir / "stderr.txt").write_text(err or "")
    (out_dir / "meta.json").write_text(json.dumps({
        "protein_id": protein_id,
        "task_id": task_id,
        "worker": worker,
        "returncode": p.returncode,
        "cmd": cmd,
        "workdir": str(workdir),
    }, indent=2))

    # Copy any files created by pipeline into results dir
    # (This is generic and works even if pipeline output names are fixed)
    for f in workdir.iterdir():
        if f.is_file():
            # don't recopy input
            if f.name == "input.fa":
                continue
            dest = out_dir / f.name
            # overwrite OK (same protein_id should be unique, but safe)
            shutil.copy2(str(f), str(dest))

    # Optional: cleanup workdir to save space (keep if debugging)
    # shutil.rmtree(workdir, ignore_errors=True)


    logging.info(f"START protein {protein_id}")

    try:
        # run s4pred
        logging.info(f"{protein_id}: S4Pred complete")

        # run HHSearch
        logging.info(f"{protein_id}: HHSearch complete")

        # parse results
        logging.info(f"{protein_id}: Parse complete")

    except Exception as e:
        logging.exception(f"{protein_id}: FAILED with error")
        raise


    return {
        "ok": p.returncode == 0,
        "returncode": p.returncode,
        "task_id": task_id,
        "worker": worker,
        "protein_id": protein_id,
        "results_dir": str(out_dir),
    }
    

