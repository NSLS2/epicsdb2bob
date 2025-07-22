"""Interface for ``python -m epicsdb2bob``."""

import logging
import os
from argparse import ArgumentParser
from pathlib import Path

from dbtoolspy import Database, load_database_file

from . import __version__
from .bobfile_gen import generate_bobfile_for_db

__all__ = ["main"]

logging.basicConfig()

logger = logging.getLogger("epicsdb2bob")


def main() -> None:
    """Argument parser for the CLI."""
    parser = ArgumentParser()
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )
    parser.add_argument(
        "-o",
        "--one-file",
        action="store_true",
        help="Generate a single bob file for all discovered records",
    )
    parser.add_argument(
        "-s",
        "--substitutions",
        action="store_true",
        help="If set, substitution files will also be parsed and generated.",
    )
    parser.add_argument(
        "-m",
        "--macros",
        nargs="+",
        type=str,
        help="Macros to apply when loading databases",
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to location in which to search for EPICS database template files",
    )
    parser.add_argument(
        "output", type=str, help="Output location for generated screens."
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args()

    logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    macros_dict = {}
    if args.macros:
        split_macros = [macro.split("=") for macro in args.macros]
        for macro in split_macros:
            macros_dict[macro[0]] = macro[1]

    databases = find_epics_dbs_templates_and_subs(
        args.input,
        include_subs=args.substitutions,
        macros=macros_dict if macros_dict else None,
    )
    for name in databases:
        generate_bobfile_for_db(name, databases[name])


def find_epics_dbs_templates_and_subs(
    search_path: Path, include_subs: bool = False, macros: dict[str, str] | None = None
) -> dict[str, Database]:
    epics_databases: dict[str, Database] = {}
    for dirpath, _, filenames in os.walk(search_path):
        for file in filenames:
            full_file_path = os.path.join(dirpath, file)
            if file.endswith((".db", ".template")):
                try:
                    epics_databases[file.split(".", -1)[0]] = load_database_file(
                        full_file_path, macros=macros
                    )
                    logger.info(f"Parsed {full_file_path}")
                except StopIteration:
                    logger.warning(
                        f"Failed to parse {full_file_path} as an EPICS database"
                    )
            # elif file.endswith(".substitutions") and include_subs:
            #     try:
            #         epics_databases[file.split(".", -1)[0]] = load_template_file(full_file_path)
            #         logger.info(f"Parsed {full_file_path}")
            #     except:
            #         logger.warning(f"Failed to parse {full_file_path} as an EPICS substitution template")

    return epics_databases


if __name__ == "__main__":
    main()
