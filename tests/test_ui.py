from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_load_and_reject():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20).run()
    assert not app.exception
    next(b for b in app.button if b.label == "Load sample").click().run()
    assert not app.exception
    assert app.metric[0].value == "18"
    for page in ["Issues & Findings", "Agent Activity", "Evaluation", "Reports"]:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception
    next(b for b in app.button if b.label == "Prepare this report for approval").click().run()
    next(b for b in app.button if b.label == "Reject").click().run()
    assert not app.exception
    assert app.session_state["store"].audit[-1]["approved"] is False
