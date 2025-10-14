<<<<<<< Updated upstream
from epicsdb2bob.parser import (
    order_dbs_by_includes,
=======
import pytest
from epicsdb2bob.parser import (
    order_dbs_by_includes,
    find_epics_dbs_and_templates,
    find_epics_subs,
>>>>>>> Stashed changes
)


def test_order_dbs_by_includes_already_in_order(compound_db):
    simple_db, compound_db = compound_db
    ordered_dbs = order_dbs_by_includes({"simple": simple_db, "compound": compound_db})
    assert list(ordered_dbs.keys()) == ["simple", "compound"]


def test_order_dbs_by_includes_out_of_order(compound_db):
    simple_db, compound_db = compound_db
    ordered_dbs = order_dbs_by_includes({"compound": compound_db, "simple": simple_db})
    assert list(ordered_dbs.keys()) == ["simple", "compound"]
