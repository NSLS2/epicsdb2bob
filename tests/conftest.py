import pytest
from typing import Callable
from dbtoolspy import Record, Database, load_database_file, load_template_file
from epicsdb2bob.config import DEFAULT_RTYP_TO_WIDGET_MAP

RTYP_IN_DEFAULT_MAP = set(DEFAULT_RTYP_TO_WIDGET_MAP.keys())

@pytest.fixture
def simple_record_factory() -> Callable[[str, str], Record]:
    def _record_factory(rtyp: str, name: str) -> Record:
        record = Record()
        record.rtyp = rtyp # type: ignore
        record.name = name # type: ignore
        record.fields = {  # type: ignore
            "DESC": f"Test: {name}",
        }
        return record

    return _record_factory

@pytest.fixture
def readback_record_factory() -> Callable[[Record], Record]:
    def _readback_factory(out_record: Record) -> Record:
        if out_record.rtyp.endswith("o"): # type: ignore
            rtyp = out_record.rtyp[:-1] + "i" # type: ignore
        else:
            rtyp = out_record.rtyp + "in" # type: ignore
        record = Record()
        record.rtyp = rtyp # type: ignore
        record.name = out_record.name + "_RBV" # type: ignore
        record.fields = {  # type: ignore
            "DESC": f"Test: {out_record.name} RB",
        }
        return record

    return _readback_factory

@pytest.fixture
def simple_db_factory(simple_record_factory) -> Callable[[str], Database]:
    def _db_factory(name: str) -> Database:
        db = Database()
        for rtyp in RTYP_IN_DEFAULT_MAP:
            for i in range(2):
                record = simple_record_factory(rtyp, f"{name}_{rtyp}_{i+1}")
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
        if record.rtyp.endswith("o") or record.rtyp.endswith("out"):
            rb_record = readback_record_factory(record)
            db_with_readbacks.add_record(rb_record)
    return db_with_readbacks


@pytest.fixture
def compound_db(simple_db_factory, db_with_readbacks) -> tuple[Database, Database]:
    db = simple_db_factory("simple")
    compound_db = simple_db_factory("compound")
    compound_db.add_included_template("simple.template")
    return db, compound_db