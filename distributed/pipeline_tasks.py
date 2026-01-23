# pipeline_tasks.py
import os
import subprocess
from celery import Celery

# Broker URL injected by Ansible or shell env
BROKER_URL = os.environ.get("CELERY_BROKER_URL")
if not BROKER_URL:
    raise RuntimeError(
        "CELERY_BROKER_URL is not set. "
        "Example: amqp://celery:celery@<host_ip>:5672//celery"
    )

# Where the pipeline scripts live on workers
PIPELINE_DIR = os.environ.get("PIPELINE_DIR", "/opt/protein_pipeline")
PIPELINE_SCRIPT = os.path.join(PIPELINE_DIR, "pipeline_script.py")

app = Celery("protein_pipeline", broker=BROKER_URL, backend="rpc://")

@app.task(bind=True, name="protein_pipeline.run_pipeline")
def run_pipeline(self, fasta_path: str) -> dict:
    """
    Task executed on workers.
    Runs pipeline_script.py on the given FASTA file path.
    """
    if not os.path.exists(PIPELINE_SCRIPT):
        return {
            "returncode": 2,
            "stdout": "",
            "stderr": f"Missing pipeline_script.py at {PIPELINE_SCRIPT}",
            "task_id": self.request.id,
            "worker": os.uname().nodename,
        }

    cmd = ["python3", PIPELINE_SCRIPT, fasta_path]

    p = subprocess.Popen(
        cmd,
        cwd=PIPELINE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = p.communicate()

    return {
        "returncode": p.returncode,
        "stdout": out,
        "stderr": err,
        "task_id": self.request.id,
        "worker": os.uname().nodename,
        "fasta_path": fasta_path,
    }
