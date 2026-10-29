import pytest

from config import normalize_db_url


@pytest.mark.parametrize("raw,expected", [
    ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
    ("postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
    ("postgresql+psycopg2://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("sqlite:///x.db", "sqlite:///x.db"),
    ("", ""),
    (None, None),
])
def test_normalize_db_url(raw, expected):
    assert normalize_db_url(raw) == expected


def test_blank_database_url_falls_back_to_sqlite(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    import importlib, config
    importlib.reload(config)
    try:
        assert config.Config.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///")
    finally:
        monkeypatch.undo()
        importlib.reload(config)
