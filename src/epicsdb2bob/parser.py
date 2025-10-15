import logging
import os
from collections import OrderedDict
from pathlib import Path

from epicsdbtools import (
    Database,
    LoadIncludesStrategy,
    load_database_file,
    load_template_file,
)

logger = logging.getLogger("epicsdb2bob")


def order_dbs_by_includes(databases: dict[str, Database]) -> OrderedDict[str, Database]:
    ordered_dbs: OrderedDict[str, Database] = OrderedDict()
    while len(ordered_dbs) < len(databases):
        start_len = len(ordered_dbs)
        for db_name, db in databases.items():
            if db_name in ordered_dbs:
                continue
            includes = db.get_included_templates()
            if all(os.path.splitext(include)[0] in ordered_dbs for include in includes):
                ordered_dbs[db_name] = db
            elif not all(
                os.path.splitext(include)[0] in databases for include in includes
            ):
                logger.warning(
                    f"Database {db_name} includes unknown templates: {includes}"
                )
                ordered_dbs[db_name] = db
        endlen = len(ordered_dbs)
        if start_len == endlen:
            raise RuntimeError("Circular includes detected among databases/templates!")
    return ordered_dbs


def find_epics_dbs_and_templates(
    search_path: Path, macros: dict[str, str] | None = None
) -> dict[str, Database]:
    epics_databases: dict[str, Database] = {}
    for dirpath, _, filenames in os.walk(search_path):
        for file in filenames:
            full_file_path = Path(dirpath) / file
            if file.endswith((".db", ".template")):
                try:
                    epics_databases[file.split(".", -1)[0]] = load_database_file(
                        full_file_path,
                        macros=macros,
                        load_includes_strategy=LoadIncludesStrategy.IGNORE,
                    )
                    logger.info(f"Parsed {full_file_path}")
                except StopIteration:
                    logger.warning(
                        f"Failed to parse {full_file_path} as an EPICS database"
                    )

    epics_databases = order_dbs_by_includes(epics_databases)

    return epics_databases


def find_epics_subs(search_path: Path) -> dict[str, dict[str, list[dict[str, str]]]]:
    epics_subs: dict[str, dict[str, list[dict[str, str]]]] = {}
    for dirpath, _, filenames in os.walk(search_path):
        for file in filenames:
            full_file_path = Path(dirpath) / file
            if file.endswith(".substitutions"):
                try:
                    dbs_and_macros: list[tuple[str, dict[str, str]]] = (
                        load_template_file(full_file_path)
                    )
                    epics_sub = {}
                    logger.info(f"Parsed {full_file_path}")
                    for db_name, macros in dbs_and_macros:
                        epics_sub.setdefault(db_name, []).append(macros)
                    epics_subs[os.path.splitext(file)[0]] = epics_sub
                except Exception as e:
                    logger.warning(
                        f"Failed to parse {full_file_path} as an EPICS subs file: {e}"
                    )

    return epics_subs
