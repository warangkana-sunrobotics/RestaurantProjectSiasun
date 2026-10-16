"""Test load_data / validate_row. The airflow package is not needed for these functions."""
import json
import sys
import types
from pathlib import Path

import pytest

DAGS = Path(__file__).resolve().parents[1] / "dags"
sys.path.insert(0, str(DAGS))

# data_modification import data_utils which import airflow -> stub it( only check_schema is used )
for name in ("airflow", "airflow.providers", "airflow.providers.postgres",
             "airflow.providers.postgres.hooks", "airflow.providers.postgres.hooks.postgres"):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules["airflow.providers.postgres.hooks.postgres"].PostgresHook = object

from datawarehouse import data_loading  # noqa: E402
from datawarehouse.data_modification import validate_row  # noqa: E402
from datawarehouse.data_utils import check_schema  # noqa: E402


def test_load_data_reads_file_of_the_logical_date(tmp_path, monkeypatch):
    (tmp_path / "RT_data_2026-09-08.json").write_text(json.dumps([{"order_id": 1}]), encoding="utf-8")
    monkeypatch.setattr(data_loading, "DATA_DIR", tmp_path)
    assert data_loading.load_data("2026-09-08") == [{"order_id": 1}]


def test_load_data_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(data_loading, "DATA_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        data_loading.load_data("2000-01-01")


def test_load_data_rejects_non_list(tmp_path, monkeypatch):
    (tmp_path / "RT_data_2026-09-09.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(data_loading, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError):
        data_loading.load_data("2026-09-09")


def test_real_sample_file_is_valid():
    rows = json.loads((DAGS.parent / "data" / "RT_data_2026-09-08.json").read_text(encoding="utf-8"))
    for r in rows:
        validate_row(r)


def test_validate_row_rejects_missing_and_negative():
    with pytest.raises(ValueError):
        validate_row({"order_id": 1, "table_id": 1, "menu": "a"})
    with pytest.raises(ValueError):
        validate_row({"order_id": 1, "table_id": 1, "menu": "a", "cost": -1})


def test_schema_allow_list():
    assert check_schema("core") == "core"
    with pytest.raises(ValueError):
        check_schema("public; DROP TABLE x")
