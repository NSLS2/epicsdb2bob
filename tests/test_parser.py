from collections.abc import Callable
from pathlib import Path

import pytest

from epicsdb2bob.utils import (
    find_epics_dbs_and_templates,
    order_dbs_by_includes,
    parse_epics_db_file,
)


def test_order_dbs_by_includes_already_in_order(compound_db):
    simple_db, compound_db = compound_db
    ordered_dbs = order_dbs_by_includes({"simple": simple_db, "compound": compound_db})
    assert list(ordered_dbs.keys()) == ["simple", "compound"]


def test_order_dbs_by_includes_out_of_order(compound_db):
    simple_db, compound_db = compound_db
    ordered_dbs = order_dbs_by_includes({"compound": compound_db, "simple": simple_db})
    assert list(ordered_dbs.keys()) == ["simple", "compound"]


def test_parse_epics_db_file_missing_file():
    with pytest.raises(FileNotFoundError):
        parse_epics_db_file(Path("non_existent_file.db"))


@pytest.mark.parametrize(
    "extension",
    [".db", ".template"],
)
def test_parse_epics_db_file(
    simple_db_file_factory: Callable[[int, str], list[Path]], extension
):
    db_files = simple_db_file_factory(1, extension)
    assert len(db_files) == 1
    db_file = db_files[0]

    epics_dbs = parse_epics_db_file(db_file)
    assert len(epics_dbs) == 1
    assert db_file.stem.split(".", -1)[0] in epics_dbs


def test_find_epics_dbs_and_templates_single_file(
    simple_db_file_factory: Callable[[int, str], list[Path]],
):
    db_files = simple_db_file_factory(1, ".db")
    assert len(db_files) == 1
    db_file = db_files[0]

    epics_dbs = find_epics_dbs_and_templates(db_file)
    assert len(epics_dbs) == 1
    assert db_file.stem.split(".", -1)[0] in epics_dbs


def test_find_epics_dbs_and_templates_directory(
    simple_db_file_factory: Callable[[int, str], list[Path]], tmp_path: Path
):
    num_dbs = 3
    db_files = simple_db_file_factory(num_dbs, ".db")
    for db_file in db_files:
        dest = tmp_path / db_file.name
        db_file.rename(dest)

    epics_dbs = find_epics_dbs_and_templates(tmp_path)
    assert len(epics_dbs) == num_dbs
    for db_file in db_files:
        assert db_file.stem.split(".", -1)[0] in epics_dbs


def test_find_epics_dbs_and_templates_compound_db(simple_db, tmp_path: Path):
    with open(tmp_path / "compound.template", "w") as f:
        f.write("include simple.template\n")

    simple_db_file = tmp_path / "simple.template"
    with open(simple_db_file, "w") as f:
        f.write(str(simple_db))

    epics_dbs = find_epics_dbs_and_templates(tmp_path)
    assert len(epics_dbs) == 2
    for i, db in enumerate(epics_dbs):
        if i == 0:
            assert db == "simple"
        elif i == 1:
            assert db == "compound"


def test_order_dbs_by_includes_circular_include(tmp_path: Path):
    with open(tmp_path / "db1.template", "w") as f:
        f.write("include db2.template\n")

    with open(tmp_path / "db2.template", "w") as f:
        f.write("include db1.template\n")

    db1 = parse_epics_db_file(tmp_path / "db1.template")["db1"]
    db2 = parse_epics_db_file(tmp_path / "db2.template")["db2"]

    databases = {"db1": db1, "db2": db2}

    with pytest.raises(RuntimeError):
        order_dbs_by_includes(databases)


def test_order_dbs_by_includes_unknown_include(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    with open(tmp_path / "db1.template", "w") as f:
        f.write("include unknown.template\n")

    db1 = parse_epics_db_file(tmp_path / "db1.template")["db1"]

    databases = {"db1": db1}

    ordered_dbs = order_dbs_by_includes(databases)
    assert list(ordered_dbs.keys()) == ["db1"]

    with caplog.at_level("WARNING"):
        order_dbs_by_includes(databases)

    assert "includes external templates" in caplog.text


def test_parse_epics_db_file_invalid(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    with open(tmp_path / "invalid.db", "w") as f:
        f.write("record(bo, )")

    with caplog.at_level("WARNING"):
        epics_dbs = parse_epics_db_file(tmp_path / "invalid.db")

    assert len(epics_dbs) == 0
    assert "Failed to parse" in caplog.text


def test_parse_epics_db_file_non_db_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    with open(tmp_path / "not_a_db.txt", "w") as f:
        f.write("Just some text.")

    with caplog.at_level("WARNING"):
        epics_dbs = parse_epics_db_file(tmp_path / "not_a_db.txt")

    assert len(epics_dbs) == 0
    assert "is not an EPICS DB or template file" in caplog.text
