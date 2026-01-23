# task_dispatcher.py
import os
from pipeline_tasks import run_pipeline

# Example FASTA(s) to run. Start with ONE for testing.
TEST_FASTA = os.environ.get("TEST_FASTA", "/data/proteins/test1.fasta")

if __name__ == "__main__":
    print(f"Dispatching pipeline task for: {TEST_FASTA}")
    res = run_pipeline.delay(TEST_FASTA)
    print(f"Submitted task_id={res.id}")

    # Optional: wait for result (good for testing; remove for large runs)
    try:
        result = res.get(timeout=30)
        print("Result received:")
        print(result)
    except Exception as e:
        print("Task submitted, not waiting (or worker not ready). Error:", e)
