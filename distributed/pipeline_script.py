import sys
from subprocess import Popen, PIPE
from Bio import SeqIO
import shutil
import os

"""
usage: python pipeline_script.py INPUT.fasta  
approx 5min per analysis
"""

# --- Configurable tool paths (override via environment variables) ---
S4PRED_RUN = os.environ.get("S4PRED_RUN", "/opt/s4pred/run_model.py")
HHSEARCH_BIN = os.environ.get("HHSEARCH_BIN", "/usr/bin/hhsearch")
HHDB = os.environ.get("HHDB", "/data/hhdb/pdb70/pdb70")

# CPU control (keep 1 by default)
S4PRED_THREADS = os.environ.get("S4PRED_THREADS", "1")
HHSEARCH_CPU = os.environ.get("HHSEARCH_CPU", "1")

def run_parser(hhr_file):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parser_path = os.path.join(script_dir, "results_parser.py")

    cmd = ['python3', parser_path, hhr_file]
    print(f'STEP 4: RUNNING PARSER: {" ".join(cmd)}')
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    print(out.decode("utf-8"))
    if err:
        print(err.decode("utf-8"), file=sys.stderr)

def run_hhsearch(a3m_file):
    """
    Run HHSearch to produce the hhr file
    """
    cmd = [
        HHSEARCH_BIN,
        "-i", a3m_file,
        "-cpu", str(HHSEARCH_CPU),
        "-d", HHDB,
        "-o", hhr_file,
    ]
    print(f'STEP 3: RUNNING HHSEARCH: {" ".join(cmd)}')
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

def read_horiz(tmp_file, horiz_file, a3m_file):
    """
    Parse horiz file and concatenate the information to a new tmp a3m file
    """
    pred = ''
    conf = ''
    print("STEP 2: REWRITING INPUT FILE TO A3M")
    with open(horiz_file) as fh_in:
        for line in fh_in:
            if line.startswith('Conf: '):
                conf += line[6:].rstrip()
            if line.startswith('Pred: '):
                pred += line[6:].rstrip()
    with open(tmp_file) as fh_in:
        contents = fh_in.read()
    with open(a3m_file, "w") as fh_out:
        fh_out.write(f">ss_pred\n{pred}\n>ss_conf\n{conf}\n")
        fh_out.write(contents)

def run_s4pred(input_file, out_file):
    """
    Runs the s4pred secondary structure predictor to produce the horiz file
    """
    cmd = ['python3', S4PRED_RUN,
        '-t', 'horiz', '-T', S4PRED_THREADS, input_file]

    print(f'STEP 1: RUNNING S4PRED: {" ".join(cmd)}')
    p = Popen(cmd, stdin=PIPE,stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    with open(out_file, "w") as fh_out:
        fh_out.write(out.decode("utf-8"))

    
def read_input(file):
    """
    Function reads a fasta formatted file of protein sequences
    """
    print("READING FASTA FILES")
    sequences = {}
    ids = []
    for record in SeqIO.parse(file, "fasta"):
        sequences[record.id] = record.seq
        ids.append(record.id)
    return(sequences)


if __name__ == "__main__":
    
    sequences = read_input(sys.argv[1])
    tmp_file = "tmp.fas"
    horiz_file = "tmp.horiz"
    a3m_file = "tmp.a3m"
    hhr_file = "tmp.hhr"
    for k, v in sequences.items():
        print(f'Now analysing input: {k}')
        with open(tmp_file, "w") as fh_out:
            fh_out.write(f">{k}\n")
            fh_out.write(f"{v}\n")
        run_s4pred(tmp_file, horiz_file)
        read_horiz(tmp_file, horiz_file, a3m_file)
        run_hhsearch(a3m_file)
        run_parser(hhr_file)
        shutil.move("hhr_parse.out", f'{k}_parse.out')