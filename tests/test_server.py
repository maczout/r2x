"""HTTP API and job queue, with a stand-in for Response (no Wine needed)."""
import io
import time
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from r2x.server.app import create_app  # noqa: E402
from r2x.server.jobs import JobManager, safe_filename  # noqa: E402
from r2x.worker.session import R2xError  # noqa: E402

TOKEN = "s3cret"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def fake_run(input_file, out, response_dir, prefix, display, progress, on_stage):
    text = Path(input_file).read_bytes()
    if b"bad" in text:
        raise R2xError("Response shows a dialog 'Invalid File': Not a valid file format")
    progress("solved: 3 load stages")
    out.mkdir(parents=True)
    (out / "input.r2t").write_bytes(text)
    for i in range(3):
        d = out / "stages" / f"{i:03d}"
        d.mkdir(parents=True)
        (d / "longitudinal_strain.txt").write_bytes(b"stage %d\r\n" % i)
        on_stage(i + 1, 3)
    (out / "manifest.json").write_text("{}")


@pytest.fixture
def client(tmp_path):
    template = tmp_path / "template"
    (template / "drive_c").mkdir(parents=True)
    (template / "system.reg").write_text("")
    m = JobManager(tmp_path / "data", 2, tmp_path / "Response", template, run=fake_run)
    m.start(displays=[":1", ":2"])
    return TestClient(create_app(m, TOKEN, {"r2x_version": "test"}, max_upload=1000))


def wait_done(client, job_id):
    for _ in range(200):
        j = client.get(f"/jobs/{job_id}", headers=AUTH).json()
        if j["status"] in ("done", "failed"):
            return j
        time.sleep(0.01)
    raise AssertionError("job did not finish")


def test_requires_token(client):
    assert client.get("/health").status_code == 401
    assert client.get("/health", headers={"Authorization": "Bearer nope"}).status_code == 401
    h = client.get("/health", headers=AUTH).json()
    assert h["workers"] == 2 and h["r2x_version"] == "test"


def test_job_round_trip(client):
    r = client.post("/jobs", headers=AUTH, files={"file": ("Newbeam.r2t", b"section data")})
    assert r.status_code == 201 and r.json()["name"] == "Newbeam"
    j = wait_done(client, r.json()["id"])
    assert j["status"] == "done" and j["stage"] == 3 and j["stage_count"] == 3
    z = client.get(f"/jobs/{j['id']}/result", headers=AUTH)
    assert z.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert "stages/002/longitudinal_strain.txt" in names and "manifest.json" in names


def test_failed_job_reports_reason(client):
    r = client.post("/jobs", headers=AUTH, files={"file": ("x.r2t", b"bad")})
    j = wait_done(client, r.json()["id"])
    assert j["status"] == "failed" and "Not a valid file format" in j["error"]
    assert client.get(f"/jobs/{j['id']}/result", headers=AUTH).status_code == 409


def test_limits(client):
    assert client.post("/jobs", headers=AUTH,
                       files={"file": ("big.r2t", b"x" * 1001)}).status_code == 413
    assert client.post("/jobs", headers=AUTH, files={"file": ("e.r2t", b"")}).status_code == 400
    assert client.get("/jobs/nope", headers=AUTH).status_code == 404


def test_safe_filename():
    assert safe_filename("C:\\cases\\Liping LB1.rsp") == "Liping LB1.rsp"
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("bé*am.r2t") == "b__am.r2t"
    assert safe_filename("") == "input.r2t"
