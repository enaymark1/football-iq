"""Fixtures: una base con datos SINTÉTICOS (ver tests/synthetic.py) y una base vacía."""
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="fiq-tests-"))
# Antes de importar la app: la configuración se lee una sola vez.
os.environ["FIQ_DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["FIQ_MODELS_DIR"] = str(_TMP / "artifacts")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.database import Base, engine, get_session, make_engine  # noqa: E402
from app.data import loader, pipeline  # noqa: E402
from app.main import app  # noqa: E402
from app.ml.training import train_all  # noqa: E402
from tests.synthetic import make_raw  # noqa: E402


@pytest.fixture(scope="session")
def raw_tables():
    return make_raw()


@pytest.fixture(scope="session")
def loaded_db(raw_tables):
    result = pipeline.build(raw_tables, source="synthetic", first_player_season=2021)
    loader.write_tables(engine, result.tables, result.report, reports_dir=None)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        train_all(s)
    return engine


@pytest.fixture()
def session(loaded_db):
    Session = sessionmaker(bind=loaded_db, expire_on_commit=False)
    with Session() as s:
        yield s


@pytest.fixture()
def client(loaded_db):
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def empty_client(tmp_path, monkeypatch):
    """API apuntando a una base sin datos y sin modelos entrenados."""
    empty_engine = make_engine(f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    Base.metadata.create_all(empty_engine)
    Session = sessionmaker(bind=empty_engine)

    def _session():
        with Session() as s:
            yield s

    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "models_dir", tmp_path / "no-models")
    app.dependency_overrides[get_session] = _session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
