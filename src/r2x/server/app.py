"""HTTP API. Every endpoint needs `Authorization: Bearer <R2X_TOKEN>`.

POST /jobs              upload one input file (multipart field "file"); returns the job
GET  /jobs/{id}         job status and progress
GET  /jobs/{id}/result  zip of the output folder, once the job is done
GET  /health            versions and queue state
"""

from __future__ import annotations

import hmac

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from r2x import __version__
from r2x.server.jobs import JobManager


def create_app(manager: JobManager, token: str, info: dict, max_upload: int = 5 << 20) -> FastAPI:
    if not token:
        raise ValueError("a token is required")
    app = FastAPI(title="r2x", version=__version__, docs_url=None, redoc_url=None)

    def auth(request: Request):
        given = request.headers.get("authorization", "")
        if not hmac.compare_digest(given.encode(), f"Bearer {token}".encode()):
            raise HTTPException(401, "missing or wrong token",
                                headers={"WWW-Authenticate": "Bearer"})

    def job_or_404(job_id: str):
        job = manager.get(job_id)
        if job is None:
            raise HTTPException(404, "no such job")
        return job

    @app.post("/jobs", status_code=201, dependencies=[Depends(auth)])
    async def create_job(file: UploadFile = File(...)):
        content = await file.read(max_upload + 1)
        if len(content) > max_upload:
            raise HTTPException(413, f"input larger than {max_upload} bytes")
        if not content:
            raise HTTPException(400, "empty input")
        return manager.submit(file.filename or "input.r2t", content).public()

    @app.get("/jobs/{job_id}", dependencies=[Depends(auth)])
    def get_job(job_id: str):
        return job_or_404(job_id).public()

    @app.get("/jobs/{job_id}/result", dependencies=[Depends(auth)])
    def get_result(job_id: str):
        job = job_or_404(job_id)
        if job.status != "done":
            raise HTTPException(409, f"job is {job.status}")
        return FileResponse(job.result, media_type="application/zip",
                            filename=f"{job.name}_r2x.zip")

    @app.get("/health", dependencies=[Depends(auth)])
    def health():
        return {"status": "ok" if manager.ready.is_set() else "starting", **info,
                **manager.stats()}

    return app
