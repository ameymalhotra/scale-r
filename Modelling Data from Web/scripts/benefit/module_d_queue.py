"""Run the remaining Module D models as one queue, detached from the terminal or app (D-193).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_d_queue.py --detach

--detach starts the queue in its own session under caffeinate (no idle or system
sleep), so closing or restarting the app or terminal does not stop it, and returns.
Jobs, each in its own process, each saving its model as soon as it finishes
(and a checkpoint right after backfitting, D-194):
1. validation: single-family main refit at tolerance 0.00002 with its saved
   bandwidths (n10000_tol2e5);
2. comparison with the saved 0.00001 model; the queue stops here if the
   flood result changes;
3. condo main with the bandwidths of the condo search held fixed, tolerance
   0.00002 (D-193, D-194);
4. to 6. condo variants frequent, dollar and with_older (main bandwidths,
   tolerance 0.00002);
7. value and tax for the two test projects (reads the n10000 models).
Progress (D-192): everything goes to queue.log (job start and end, each job's
steps, percent of the standard-error step with time left, a heartbeat every
5 minutes); status.txt always shows the current step and estimated finish;
queue.pid holds the queue's process id. All in outputs/benefit/module_d/n10000/queue/.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402
from progress import Progress, dur  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
QDIR = paths.OUT_BENEFIT / "module_d" / "n10000" / "queue"
LOG, STATUS, PID = QDIR / "queue.log", QDIR / "status.txt", QDIR / "queue.pid"
# condo search bandwidths (13 Nov, round 200): intercept, then FLOOD, log_living_area, age, bedrooms,
# bathrooms, waterfront, log_dist_water, ground_elev_ft, time
CONDO_BW = "501,503,501,501,504,882,10000,501,501,525"
FIT = str(HERE / "module_d_fit.py")
# expected seconds from the 13 Nov single-family runs (final fit about 65 minutes each)
SF_BW = "501,9993,501,501,501,3181,503,9999,9999,501,501,501"  # saved single-family main bandwidths
CONDO = {"MGWR_TOL": "2e-5"}
# (name, arguments, expected seconds, extra environment, stop the queue if it fails)
JOBS = [("single-family validation at tolerance 0.00002", [FIT, "single_family", "fixed", SF_BW], 4000,
         {"MGWR_TOL": "2e-5", "MGWR_OUTDIR": "n10000_tol2e5"}, True),
        ("tolerance comparison", [str(HERE / "module_d_tol_check.py")], 60, {}, True),
        ("condo main (fixed bandwidths)", [FIT, "condo", "fixed", CONDO_BW], 9000, CONDO, True),
        ("condo frequent", [FIT, "condo", "variants", "frequent"], 9000, CONDO, False),
        ("condo dollar", [FIT, "condo", "variants", "dollar"], 9000, CONDO, False),
        ("condo with_older", [FIT, "condo", "variants", "with_older"], 9000, CONDO, False),
        ("value and tax", [str(HERE / "module_d_value_tax.py")], 300, {}, False)]
ENV = {"MGWR_POOL": "1", "MGWR_JOBS": "-1", "MGWR_CHUNKS": "4", "MGWR_N": "10000", "MGWR_OUTDIR": "n10000",
       "MGWR_VERBOSE": "1", "MODULE_D_RUN": "n10000", "PYTHONUNBUFFERED": "1"}
# loky repeats this harmless clean-up warning thousands of times; kept out of the log
NOISE = ("resource_tracker",)


def detach():
    QDIR.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen(["caffeinate", "-is", sys.executable, "-I", "-u", __file__], cwd=ROOT,
                         start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    print(f"queue started in its own session (caffeinate pid {p.pid}); log {LOG}; status {STATUS}")


def main():
    QDIR.mkdir(parents=True, exist_ok=True)
    PID.write_text(str(os.getpid()))
    log = open(LOG, "a", buffering=1)
    sys.stdout = log
    sys.stderr = log
    P = Progress("condo queue", heartbeat=False)  # each job writes its own heartbeat
    os.environ["PROGRESS_STATUS"] = str(STATUS)
    P.status_file = str(STATUS)
    started, took, ok_all = time.time(), [], True
    for i, (name, args, expected, extra, gate) in enumerate(JOBS, 1):
        condo_done = [t for t, n in took if n.startswith("condo")]

        def guess(n, e):  # later condo jobs: the observed length of the condo jobs already done
            return sum(condo_done) / len(condo_done) if condo_done and n.startswith("condo") else e
        exp = guess(name, expected)
        later = sum(guess(n, e) for n, _, e, _, _ in JOBS[i:])
        env = {**os.environ, **ENV, **extra, "PROGRESS_EXPECTED": str(round(exp)),
               "PROGRESS_QUEUE": json.dumps({"index": i, "total": len(JOBS), "started": started,
                                             "later_expected": round(later)})}
        P.log(f"QUEUE job {i} of {len(JOBS)} START: {name} (expected about {dur(exp)}; "
              f"whole queue about {dur(exp + later)} more)")
        t = time.time()
        proc = subprocess.Popen([sys.executable, "-I", "-u", *args], cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in proc.stdout:
            if not any(k in line for k in NOISE):
                log.write(line)
        rc = proc.wait()
        took.append((time.time() - t, name))
        P.log(f"QUEUE job {i} of {len(JOBS)} {'END' if rc == 0 else f'FAILED (exit {rc})'}: {name} after "
              f"{dur(time.time() - t)}; {i} of {len(JOBS)} jobs done ({100 * i / len(JOBS):.0f}%)")
        if rc != 0:
            ok_all = False
            if gate:
                P.log(f"QUEUE stopping: later jobs depend on '{name}' (rerunning resumes from any checkpoint)")
                break
    P.finish(ok_all)
    PID.unlink(missing_ok=True)


if __name__ == "__main__":
    detach() if "--detach" in sys.argv else main()
