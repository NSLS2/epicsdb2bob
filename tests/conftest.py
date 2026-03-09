from collections.abc import Callable
from pathlib import Path

import pytest
from epicsdbtools import Database, Record, RecordType
from phoebusgen.widget import Label

from epicsdb2bob.config import DEFAULT_RTYPE_TO_WIDGET_MAP, EPICSDB2BOBConfig


@pytest.fixture
def simple_record_factory() -> Callable[[str, str], Record]:
    def _record_factory(rtype: str, name: str) -> Record:
        record = Record(name, RecordType[rtype.upper()])  # type: ignore
        record.fields = {  # type: ignore
            "DESC": f"{name.upper()} desc",
        }
        return record

    return _record_factory


@pytest.fixture
def readback_record_factory() -> Callable[[Record], Record]:
    def _readback_factory(out_record: Record) -> Record:
        if out_record.rtype.endswith("o"):  # type: ignore
            rtype = out_record.rtype[:-1] + "i"  # type: ignore
        else:
            rtype = out_record.rtype[:-3] + "in"  # type: ignore
        record = Record(out_record.name + "_RBV", RecordType[rtype.upper()])  # type: ignore
        record.fields = {  # type: ignore
            "DESC": f"{out_record.name.upper()} RB desc",  # type: ignore
        }
        return record

    return _readback_factory


@pytest.fixture
def simple_db_factory(simple_record_factory) -> Callable[[str], Database]:
    def _db_factory(name: str) -> Database:
        db = Database()
        for rtype in DEFAULT_RTYPE_TO_WIDGET_MAP.keys():
            for i in range(2):
                record = simple_record_factory(rtype, f"{name}_{rtype}_{i + 1}")
                db.add_record(record)
        return db

    return _db_factory


@pytest.fixture
def simple_db(simple_db_factory) -> Database:
    return simple_db_factory("test")


@pytest.fixture
def db_with_readbacks(simple_db, readback_record_factory) -> Database:
    db_with_readbacks = simple_db.copy()
    for record in list(db_with_readbacks.values()):
        if record.rtype.endswith("o") or record.rtype.endswith("out"):
            rb_record = readback_record_factory(record)
            db_with_readbacks.add_record(rb_record)
    return db_with_readbacks


@pytest.fixture
def compound_db(simple_db_factory) -> tuple[Database, Database]:
    db = simple_db_factory("simple")
    compound_db = simple_db_factory("compound")
    compound_db.add_included_template("simple.template", database=None)
    return db, compound_db


@pytest.fixture
def default_config() -> EPICSDB2BOBConfig:
    return EPICSDB2BOBConfig()


@pytest.fixture
def simple_label() -> Label:
    return Label("SimpleLabel", "Text", 10, 10, 100, 30)


@pytest.fixture
def simple_db_file_factory(
    tmp_path, simple_db_factory
) -> Callable[[int, str], list[Path]]:
    def _db_file_factory(num_dbs: int, extension: str = ".db") -> list[Path]:
        db_file_paths = []
        for i in range(num_dbs):
            name = f"simple_db_{i + 1}"
            db = simple_db_factory(name)
            db_file_path = tmp_path / f"{name}{extension}"
            with open(db_file_path, "w") as f:
                f.write(str(db))
            db_file_paths.append(db_file_path)
        return db_file_paths

    return _db_file_factory
