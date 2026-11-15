"""Progress reporting standard for long-running scripts (D-192).

Every script that can run for more than a few minutes uses this module:
- each step logs its start and end time and how long it took;
- where the work can be counted (chunks, models in a queue), each update logs
  percent done and an estimated time remaining from the rate observed so far;
- a heartbeat line every 5 minutes (PROGRESS_HEARTBEAT seconds) shows the job
  is alive even inside a step that cannot be counted;
- one short status file (PROGRESS_STATUS, plain text) always shows the
  current step, percent done and the estimated finish, rewritten in place.
Queue runners pass PROGRESS_QUEUE (JSON: index, total, started, later_expected
seconds) so a job can show the whole queue's estimated finish as well.

    from progress import Progress
    P = Progress("condo main")
    P.start("standard errors", total=40)
    P.update(12)
    P.end()
    P.finish()
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta


def stamp(t=None):
    return datetime.fromtimestamp(t or time.time()).strftime("%a %H:%M:%S")


def dur(s):
    s = int(max(s, 0))
    return f"{s // 3600}h {s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m {s % 60:02d}s"


class Progress:
    def __init__(self, job, expected=None, heartbeat=True):
        self.job = job
        self.status_file = os.environ.get("PROGRESS_STATUS")
        self.queue = json.loads(os.environ.get("PROGRESS_QUEUE", "null") or "null")
        self.expected = float(expected or os.environ.get("PROGRESS_EXPECTED", 0) or 0) or None
        self.t0 = time.time()
        self.step, self.t_step, self.done, self.total = "starting", self.t0, None, None
        self.lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.log(f"START job '{job}'" + (f" (expected about {dur(self.expected)} from earlier runs)" if self.expected else ""))
        self.write()
        every = int(os.environ.get("PROGRESS_HEARTBEAT", "300"))
        if heartbeat and every > 0:
            threading.Thread(target=self._beat, args=(every,), daemon=True).start()

    def log(self, msg):
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)

    def start(self, step, total=None):
        with self.lock:
            self.step, self.t_step, self.done, self.total = step, time.time(), (0 if total else None), total
        self.log(f"STEP START {step}" + (f" ({total} parts)" if total else ""))
        self.write()

    def update(self, done, total=None):
        with self.lock:
            self.done, self.total = done, total or self.total
        r = self.step_remaining()
        self.log(f"PROGRESS {self.step}: {done} of {self.total} ({self.pct():.0f}%), elapsed {dur(time.time() - self.t_step)}"
                 + (f", about {dur(r)} left, step done about {stamp(time.time() + r)}" if r is not None else ""))
        self.write()

    def end(self):
        self.log(f"STEP END {self.step} after {dur(time.time() - self.t_step)}")
        with self.lock:
            self.done = self.total
        self.write()

    def finish(self, ok=True):
        with self.lock:
            self.step, self.done, self.total = ("finished" if ok else "FAILED"), None, None
            self.expected, self.queue = None, None
        self.log(f"{'END' if ok else 'FAILED'} job '{self.job}' after {dur(time.time() - self.t0)}")
        self.write()

    def pct(self):
        return 100.0 * self.done / self.total if self.total else 0.0

    def step_remaining(self):
        if self.total and self.done:
            return (time.time() - self.t_step) / self.done * (self.total - self.done)
        return None

    def job_remaining(self):
        """Counted step's own estimate when available, else the expected job length from earlier runs."""
        r = self.step_remaining()
        if r is not None:
            return r + 60
        if self.expected:
            return max(self.expected - (time.time() - self.t0), 0)
        return None

    def write(self):
        if not self.status_file:
            return
        now = time.time()
        r = self.job_remaining()
        lines = [f"updated      {stamp(now)}   (pid {os.getpid()})",
                 f"job          {self.job}   running {dur(now - self.t0)}",
                 f"step         {self.step}   since {stamp(self.t_step)}"]
        if self.total:
            lines.append(f"step done    {self.done} of {self.total} ({self.pct():.0f}%)")
        if r is not None:
            lines.append(f"job finish   about {stamp(now + r)}   ({dur(r)} left)")
        if self.queue:
            q = self.queue
            lines.append(f"queue        job {q['index']} of {q['total']}, started {stamp(q['started'])}")
            if r is not None:
                lines.append(f"queue finish about {stamp(now + r + q.get('later_expected', 0))}")
        # one writer at a time, a temporary file per thread, and a failed status write never stops the job
        # (D-194: two threads writing the same temporary file at once crashed a 9-hour fit)
        try:
            with self.write_lock:
                tmp = f"{self.status_file}.{os.getpid()}.{threading.get_ident()}.tmp"
                with open(tmp, "w") as f:
                    f.write("\n".join(lines) + "\n")
                os.replace(tmp, self.status_file)
        except Exception as e:  # status file is a convenience; the log and the model matter
            print(f"[status file not written: {e!r}]", flush=True)

    def _beat(self, every):
        while True:
            time.sleep(every)
            r = self.job_remaining()
            self.log(f"HEARTBEAT job '{self.job}', step '{self.step}'"
                     + (f" {self.pct():.0f}%" if self.total else "")
                     + f", running {dur(time.time() - self.t0)}"
                     + (f", job finish about {stamp(time.time() + r)}" if r is not None else ""))
            self.write()


def joblib_progress(P, step, min_tasks=20):
    """Patch a module's joblib Parallel so a large parallel call reports each finished task to P.

    Returns a Parallel subclass; assign it to the module's Parallel name (e.g. mgwr.gwr.Parallel).
    Calls with fewer than min_tasks tasks (small searches) are left silent.
    """
    from joblib import Parallel

    class ProgressParallel(Parallel):
        def __call__(self, iterable):
            tasks = list(iterable)
            self._p_on = len(tasks) >= min_tasks
            self._p_n = len(tasks)
            if self._p_on:
                P.start(step, total=len(tasks))
            out = super().__call__(tasks)
            if self._p_on:
                P.end()
            return out

        def print_progress(self):
            if getattr(self, "_p_on", False):
                P.update(self.n_completed_tasks, self._p_n)

    return ProgressParallel
