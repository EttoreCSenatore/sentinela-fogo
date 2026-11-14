import os
import tempfile

# Configure before any app import: temp DB, no background network tasks.
_tmp = tempfile.mkdtemp(prefix="sentinela-test-")
os.environ["SENTINELA_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["SENTINELA_MQTT_ENABLED"] = "false"
os.environ["SENTINELA_INPE_ENABLED"] = "false"
os.environ["SENTINELA_WEATHER_ENABLED"] = "false"
os.environ["SENTINELA_TELEGRAM_BOT_ENABLED"] = "false"
os.environ["SENTINELA_INPE_RISK_ENABLED"] = "false"
os.environ["SENTINELA_INGEST_TOKEN"] = "test-ingest-token"
os.environ["SENTINELA_SITES_FILE"] = "/nonexistent/sites.json"
os.environ["SENTINELA_RECIPIENTS_FILE"] = "/nonexistent/recipients.json"
os.environ.pop("SENTINELA_TELEGRAM_BOT_TOKEN", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    # Sends the ingest token by default, as a legitimate gateway would; see test_security.py for the unauthenticated case.
    with TestClient(app, headers={"X-Ingest-Token": "test-ingest-token"}) as c:
        yield c
