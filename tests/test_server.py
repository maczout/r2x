"""HTTP API and job queue, with a stand-in for Response (no Wine needed)."""
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from r2x import record  # noqa: E402
from r2x.progress import Event  # noqa: E402
from r2x.server.app import create_app  # noqa: E402
from r2x.server.jobs import JobManager, safe_filename  # noqa: E402
from r2x.worker.session import R2xError  # noqa: E402

TOKEN = "s3cret"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def fake_run(input_file, out, response_dir, prefix, display, stages, on_event):
    text = Path(input_file).read_bytes()
    if b"bad" in text:
        raise R2xError("Response shows a dialog 'Invalid File': Not a valid file format")
    on_event(Event("solved", count=3, stage=2))
    targets = stages.resolve(3, 2)
    sections = []
    for k, i in enumerate(targets):
        sections.append((f"stage/{i}/longitudinal_strain", b"stage %d\r\n" % i))
        on_event(Event("stage", stage=i, done=k + 1, total=len(targets)))
    out.write_bytes(record.encode({"input-name": Path(input_file).name}, sections))


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
    r = client.post("/jobs", headers=AUTH, files={"file": ("Newbeam.r2t", b"section data")},
                    data={"stage": "all"})
    assert r.status_code == 201 and r.json()["name"] == "Newbeam" and r.json()["stages"] == "all"
    j = wait_done(client, r.json()["id"])
    assert j["status"] == "done" and j["stage"] == 3 and j["stage_total"] == 3
    assert j["stage_count"] == 3
    res = client.get(f"/jobs/{j['id']}/result", headers=AUTH)
    assert res.status_code == 200
    rec = record.decode(res.content)
    assert rec.header["input-name"] == "Newbeam.r2t" and rec.stages() == [0, 1, 2]


def test_default_stage_is_peak(client):
    r = client.post("/jobs", headers=AUTH, files={"file": ("a.r2t", b"x")})
    j = wait_done(client, r.json()["id"])
    rec = record.decode(client.get(f"/jobs/{j['id']}/result", headers=AUTH).content)
    assert rec.stages() == [2]


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
    assert client.post("/jobs", headers=AUTH, files={"file": ("a.r2t", b"x")},
                       data={"stage": "5-1"}).status_code == 400


def test_safe_filename():
    assert safe_filename("C:\\cases\\Liping LB1.rsp") == "Liping LB1.rsp"
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("bé*am.r2t") == "b__am.r2t"
    assert safe_filename("") == "input.r2t"
