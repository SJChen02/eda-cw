# pipeline_tasks.py
import os
import subprocess
from celery import Celery

# Broker URL injected by Ansible or shell env
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

BROKER_URL = os.environ.get("CELERY_BROKER_URL") or load_sysconfig_value("CELERY_BROKER_URL") or "amqp://celery:celery@10.134.12.197:5672//celery"

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

# # -----------------------
# # Smoke test tasks
# # -----------------------
# import socket
# import pathlib

# @app.task(name="smoke.ping")
# def ping():
#     return {"worker": socket.gethostname(), "ok": True}

# @app.task(name="smoke.check_tools")
# def check_tools():
#     def cmd_ok(cmd):
#         try:
#             subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
#             return True
#         except Exception:
#             return False

#     return {
#         "worker": socket.gethostname(),
#         "env_has_broker": "CELERY_BROKER_URL" in os.environ,
#         "pipeline_dir_exists": os.path.isdir(os.environ.get("PIPELINE_DIR", "")),
#         "hhsearch_ok": cmd_ok(["hhsearch", "-h"]),
#         "s4pred_ok": cmd_ok(["python3", "/opt/s4pred/run_model.py", "-h"]),
#     }

# @app.task(name="smoke.write_file")
# def write_file():
#     p = pathlib.Path("/tmp/celery_smoke_test.txt")
#     p.write_text(f"hello from {socket.gethostname()}\n")
#     return {"worker": socket.gethostname(), "wrote": str(p)}