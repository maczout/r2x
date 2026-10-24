"""Job queue and workers.

Each worker owns one virtual display and one copy of the Wine prefix. Response's chart data goes
through the clipboard, and the clipboard belongs to the Wine prefix (one wineserver) and the X
display, so workers sharing either would read each other's exports.
"""

from __future__ import annotations

import logging
import queue
import re
import secrets
import shutil
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from r2x.worker.runner import run_job, start_xvfb

log = logging.getLogger("r2x.server")


@dataclass
class Job:
    id: str
    name: str          # input file stem, as uploaded
    filename: str      # safe file name the input is stored under
    dir: Path
    status: str = "queued"           # queued | running | done | failed
    stage: int = 0
    stage_count: int | None = None
    message: str = ""
    error: str | None = None
    created: float = field(default_factory=time.time)
    started: float | None = None
    finished: float | None = None

    @property
    def result(self) -> Path:
        return self.dir / "result.zip"

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "status": self.status, "stage": self.stage,
                "stage_count": self.stage_count, "message": self.message, "error": self.error,
                "created": self.created, "started": self.started, "finished": self.finished}


def safe_filename(name: str) -> str:
    """Base name with anything unusual replaced; keeps the extension Response uses."""
    base = re.split(r"[\\/]", name or "")[-1].strip() or "input.r2t"
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base)
    return base.lstrip(".") or "input.r2t"


class JobManager:
    def __init__(self, data: Path, workers: int, response_dir: Path, template_prefix: Path,
                 retention_hours: float = 24, run=run_job):
        self.data = Path(data)
        self.workers = workers
        self.response_dir = Path(response_dir)
        self.template_prefix = Path(template_prefix)
        self.retention = retention_hours * 3600
        self.run = run
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.queue: queue.Queue[Job] = queue.Queue()
        self.ready = threading.Event()

    # -- lifecycle ----------------------------------------------------------------------------
    def start(self, displays: list[str] | None = None):
        """Prepare one prefix and display per worker, then start the worker threads."""
        jobs_dir = self.data / "jobs"
        shutil.rmtree(jobs_dir, ignore_errors=True)   # jobs do not survive a restart
        jobs_dir.mkdir(parents=True)
        for i in range(self.workers):
            prefix = self.data / "prefixes" / f"w{i}"
            if not (prefix / "system.reg").exists():
                shutil.rmtree(prefix, ignore_errors=True)
                shutil.copytree(self.template_prefix, prefix, symlinks=True)
            display = displays[i] if displays else start_xvfb()[1]
            log.info("worker %d: display %s, prefix %s", i, display, prefix)
            threading.Thread(target=self._work, args=(i, prefix, display), daemon=True,
                             name=f"worker-{i}").start()
        threading.Thread(target=self._clean, daemon=True, name="cleanup").start()
        self.ready.set()

    # -- jobs ---------------------------------------------------------------------------------
    def submit(self, filename: str, content: bytes) -> Job:
        job_id = secrets.token_hex(8)
        safe = safe_filename(filename)
        job = Job(job_id, Path(safe).stem, safe, self.data / "jobs" / job_id)
        job.dir.mkdir(parents=True)
        (job.dir / safe).write_bytes(content)
        with self.lock:
            self.jobs[job_id] = job
        self.queue.put(job)
        return job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)

    def stats(self) -> dict:
        with self.lock:
            states = [j.status for j in self.jobs.values()]
        return {"workers": self.workers, "queued": states.count("queued"),
                "running": states.count("running")}

    def _work(self, i: int, prefix: Path, display: str):
        while True:
            job = self.queue.get()
            if job.id not in self.jobs:      # removed while queued
                continue
            job.status, job.started = "running", time.time()

            def progress(msg, job=job):
                job.message = msg
                m = re.match(r"solved: (\d+) load stages", msg)
                if m:
                    job.stage_count = int(m.group(1))

            def on_stage(k, n, job=job):
                job.stage, job.stage_count = k, n

            out = job.dir / "out"
            try:
                self.run(job.dir / job.filename, out, self.response_dir, prefix, display,
                         progress=progress, on_stage=on_stage)
                with zipfile.ZipFile(job.result, "w", zipfile.ZIP_DEFLATED) as z:
                    for p in sorted(out.rglob("*")):
                        if p.is_file():
                            z.write(p, p.relative_to(out).as_posix())
                job.status = "done"
            except Exception as e:  # noqa: BLE001 - report every failure to the client
                log.exception("job %s failed", job.id)
                job.status, job.error = "failed", str(e) or type(e).__name__
            finally:
                shutil.rmtree(out, ignore_errors=True)
                job.finished = time.time()
                log.info("job %s (%s) %s in %.1f s on worker %d", job.id, job.name, job.status,
                         job.finished - job.started, i)

    def _clean(self):
        while True:
            time.sleep(600)
            cutoff = time.time() - self.retention
            with self.lock:
                old = [j for j in self.jobs.values() if j.finished and j.finished < cutoff]
                for j in old:
                    del self.jobs[j.id]
            for j in old:
                shutil.rmtree(j.dir, ignore_errors=True)
