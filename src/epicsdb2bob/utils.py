import logging
import os
from collections import OrderedDict
from pathlib import Path

import rpack
from epicsdbtools import (
    Database,
    LoadIncludesStrategy,
    Substitution,
    load_database_file,
    load_substitution_file,
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
            # Only consider includes that are in the local database set
            local_includes = [
                inc for inc in includes
                if os.path.splitext(inc)[0] in databases
            ]
            external_includes = [
                inc for inc in includes
                if os.path.splitext(inc)[0] not in databases
            ]
            if external_includes:
                logger.warning(
                    f"Database {db_name} includes external templates: {external_includes}"
                )
            if all(os.path.splitext(inc)[0] in ordered_dbs for inc in local_includes):
                ordered_dbs[db_name] = db
        endlen = len(ordered_dbs)
        if start_len == endlen:
            raise RuntimeError("Circular includes detected among databases/templates!")
    return ordered_dbs


def parse_epics_db_file(file_path: Path) -> dict[str, Database]:
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"EPICS DB file not found: {file_path}")
    elif file_path.suffix not in (".db", ".template"):
        logger.warning(f"File is not an EPICS DB or template file: {file_path}")
        return {}

    try:
        database = load_database_file(
            file_path, load_includes_strategy=LoadIncludesStrategy.IGNORE
        )
        logger.info(f"Parsed {file_path}")
        return {file_path.stem.split(".", -1)[0]: database}
    except StopIteration:
        logger.warning(f"Failed to parse {file_path} as an EPICS database")
        return {}


def find_epics_dbs_and_templates(
    search_path: Path, macros: dict[str, str] | None = None
) -> dict[str, Database]:
    epics_databases: dict[str, Database] = {}

    if os.path.isfile(search_path):
        return parse_epics_db_file(search_path)

    for dirpath, _, filenames in os.walk(search_path):
        for file in filenames:
            full_file_path = Path(dirpath) / file
            epics_databases.update(parse_epics_db_file(full_file_path))

    epics_databases = order_dbs_by_includes(epics_databases)

    return epics_databases


def find_epics_subs(search_path: Path) -> dict[str, dict[str, list[dict[str, str]]]]:
    epics_subs: dict[str, dict[str, list[dict[str, str]]]] = {}
    for dirpath, _, filenames in os.walk(search_path):
        for file in filenames:
            full_file_path = Path(dirpath) / file
            if file.endswith(".substitutions"):
                try:
                    subs: list[Substitution] = load_substitution_file(full_file_path)
                    epics_sub = {}
                    logger.info(f"Parsed {full_file_path}")
                    for sub in subs:
                        epics_sub.setdefault(sub.file, []).append(sub.macros)
                    epics_subs[os.path.splitext(file)[0]] = epics_sub
                except Exception as e:
                    logger.warning(
                        f"Failed to parse {full_file_path} as an EPICS subs file: {e}"
                    )

    return epics_subs


def find_bobfiles_in_search_path(bobfile_search_path: list[Path]) -> dict[str, Path]:
    written_bobfiles: dict[str, Path] = {}

    for bobfile_dir in bobfile_search_path:
        for dirpath, _, filenames in os.walk(bobfile_dir):
            for filename in filenames:
                if filename.endswith((".bob", ".opi")):
                    full_path = Path(os.path.join(dirpath, filename))
                    logger.info(f"Found additional bob/opi file: {full_path}")
                    written_bobfiles[filename] = full_path
    return written_bobfiles


def pack_close_to_square(
    rectangle_sizes: list[tuple[int, int]], max_height: int, padding: int
) -> list[tuple[int, int]]:
    """Pack rectangles into as close to a square as possible.

    Arguments
    ---------
    rectangle_sizes : list[tuple[int, int]]
        List of (width, height) for each rect
    max_height : int
        Maximum allowed height for the packed rectangles.
    padding : int
        Padding to add around each rectangle.

    Returns
    -------
    list[tuple[int, int]]
        List of (x, y) positions for each packed rectangle.
    """

    # Add padding to each rectangle size
    padded_rectangle_sizes = [
        (width + padding, height + padding) for width, height in rectangle_sizes
    ]

    height = 100
    width = 100
    increment = 100

    iteration = 0
    while True:
        try:
            if height < width and height + increment <= max_height:
                height += increment
            else:
                width += increment
            packed_x_y_positions = rpack.pack(padded_rectangle_sizes, width, height)
            break
        except rpack.PackingImpossibleError as err:
            iteration += 1
            if iteration > 1000:
                raise RuntimeError("Unable to pack rects within max height.") from err
            else:
                logger.warning(
                    f"Packing impossible at dims {width}x{height}, increasing size."
                )

    return packed_x_y_positions
