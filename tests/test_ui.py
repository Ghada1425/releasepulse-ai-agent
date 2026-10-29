from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from releasepulse.security import ReportStore

ROOT = Path(__file__).parents[1]
SAMPLES = ROOT / "data" / "samples"


@pytest.fixture
def app(tmp_path):
    test = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    test.session_state["store"] = ReportStore(tmp_path / "reports")
    return test.run()


def click(app, label):
    return next(b for b in app.button if b.label == label).click().run()


def upload(app, name, data):
    return app.file_uploader[0].set_value((name, data, "text/csv")).run()


def test_dashboard_load_and_reject(app):
    assert not app.exception
    click(app, "Load sample")
    assert not app.exception
    assert app.metric[0].value == "18"
    for page in ["Issues & Findings", "Agent Activity", "Evaluation", "Reports"]:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception
    click(app, "Prepare this report for approval")
    click(app, "Reject")
    assert not app.exception
    store = app.session_state["store"]
    assert store.audit[-1]["approved"] is False
    assert not store.root.exists()


def test_approve_writes_exact_previewed_report(app):
    click(app, "Load sample")
    app.sidebar.radio[0].set_value("Reports").run()
    click(app, "Prepare this report for approval")
    click(app, "Approve & save")
    assert not app.exception
    store = app.session_state["store"]
    reports = list(store.root.glob("report-*.json"))
    assert len(reports) == 1
    assert reports[0].read_bytes() == app.session_state["download"]
    assert store.audit[-1]["approved"] is True


def test_rejected_upload_clears_previous_data(app):
    click(app, "Load sample")
    assert app.metric[0].value == "18"
    upload(app, "broken.csv", b"foo,bar\n1,2")
    assert not app.exception
    assert any("Upload rejected" in e.value for e in app.error)
    assert "rows" not in app.session_state
    assert len(app.metric) == 0


def test_rejected_upload_names_the_invalid_row(app):
    data = (SAMPLES / "healthy.csv").read_text().replace(",passed,", ",unknown,", 1)
    upload(app, "bad-status.csv", data.encode())
    assert any("Row 2" in e.value and "status" in e.value for e in app.error)


def test_sample_button_overrides_previous_upload(app):
    upload(app, "healthy.csv", (SAMPLES / "healthy.csv").read_bytes())
    assert app.session_state["source"] == "healthy.csv"
    sample = next(s for s in app.selectbox if s.label == "Synthetic sample")
    sample.set_value("release_candidate.csv").run()
    click(app, "Load sample")
    assert app.session_state["source"] == "release_candidate.csv"
    assert any("HOLD" in w.value for w in app.error)
    app.sidebar.radio[0].set_value("Upload & Analysis").run()
    assert app.session_state["source"] == "release_candidate.csv"


def test_agent_without_key_reports_configuration_error(app, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    click(app, "Load sample")
    click(app, "Run agent analysis")
    assert not app.exception
    assert any("OPENROUTER_API_KEY" in e.value for e in app.error)
    assert "run" not in app.session_state
