"""Interface for ``python -m epicsdb2bob``."""

import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path

from dbtoolspy import Database, load_database_file, load_template_file

from . import __version__
from .bobfile_gen import generate_bobfile_for_db, generate_bobfile_for_substitution
from .config import EPICSDB2BOBConfig, EmbedLevel, MacroSetLevel, TitleBarFormat
from .palettes import WIDGET_PALETTES
from .parser import find_epics_dbs_and_templates, find_epics_subs

__all__ = ["main"]

logging.basicConfig()

logger = logging.getLogger("epicsdb2bob")


class ColorFormatter(logging.Formatter):
    """ANSI color formatter for warnings and errors."""

    COLOR_MAP = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33;1m",  # Bright Yellow
        logging.ERROR: "\033[31;1m",  # Bright Red
        logging.CRITICAL: "\033[41;97m",  # White on Red bg
    }
    RESET = "\033[0m"

    def __init__(self, fmt: str, use_color: bool = True):
        super().__init__(fmt)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        if self.use_color and record.levelno in self.COLOR_MAP:
            return f"{self.COLOR_MAP[record.levelno]}{base}{self.RESET}"
        return base


handler = logging.StreamHandler()
use_color = sys.stderr.isatty()
fmt = "%(asctime)s | %(levelname)-8s | %(message)s"
handler.setFormatter(ColorFormatter(fmt, use_color=use_color))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


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
        "input_path",
        type=str,
        help="Path to location in which to search for EPICS database template files",
    )
    parser.add_argument(
        "output_path", type=str, help="Output location for generated screens."
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "-e",
        "--embed",
        type=str,
        choices=["none", "single", "all"],
        default="single",
        help="Sets whether to embed screens when generating substitution file or not.",
    )
    parser.add_argument(
        "-m",
        "--macros",
        nargs="+",
        type=str,
        help="Macros to apply when loading databases",
    )
    parser.add_argument(
        "-t",
        "--title_bar_format",
        type=str,
        choices=["none", "minimal", "full"],
        default="minimal",
    )

    parser.add_argument(
        "-r",
        "--readback_suffix",
        type=str,
        default="_RBV",
        help="Suffix to check for when matching setpoint and readback records.",
    )
    parser.add_argument(
        "-b",
        "--bobfile_search_path",
        type=str,
        nargs="+",
        default=[],
        help="Dirs to search for addtl .bob files for generating substitution screens.",
    )
    parser.add_argument(
        "--builtin_palette",
        type=str,
        default="default",
        choices=WIDGET_PALETTES.keys(),
        help="Color palette to use.",
    )
    parser.add_argument(
        "--macro_set_level",
        type=str,
        choices=["launcher", "screen", "widget"],
        default="launcher",
        help="Level at which to apply macros when generating screens.",
    )

    args = parser.parse_args()

    logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    if os.path.exists(".epicsdb2bob.yml"):
        config: EPICSDB2BOBConfig = EPICSDB2BOBConfig.from_yaml(
            Path(".epicsdb2bob.yml"), vars(args)
        )
        if config.debug:
            logger.setLevel(logging.DEBUG)
        logger.debug("Loaded configuration from .epicsdb2bob.yml")
    else:
        config = EPICSDB2BOBConfig()
        logger.debug("No configuration file found, using defaults.")
        for key, value in vars(args).items():
            if value is not None:
                setattr(config, key, value)

    written_bobfiles: dict[str, Path] = {}

    for bobfile_dir in config.bobfile_search_path:
        for dirpath, _, filenames in os.walk(bobfile_dir):
            for filename in filenames:
                if filename.endswith((".bob", ".opi")):
                    full_path = Path(os.path.join(dirpath, filename))
                    logger.info(f"Found additional bob/opi file: {full_path}")
                    written_bobfiles[filename] = full_path

    macros = {macro.split("=")[0]: macro.split("=")[1] for macro in args.macros} if args.macros else {}

    databases = find_epics_dbs_and_templates(args.input_path, macros)
    for name in databases:
        screen = generate_bobfile_for_db(name, databases[name], macros, config)

        full_output_path = os.path.join(args.output_path, f"{name}.bob")
        screen.write_screen(full_output_path)
        written_bobfiles[os.path.basename(full_output_path)] = Path(full_output_path)


    substitutions = find_epics_subs(args.input_path)

    for substitution in substitutions:
        screen = generate_bobfile_for_substitution(
            substitution,
            substitutions[substitution],
            written_bobfiles,
            args.embed,
        )
        full_output_path = os.path.join(args.output_path, f"{substitution}.bob")
        screen.write_screen(full_output_path)
        written_bobfiles[os.path.basename(full_output_path)] = Path(full_output_path)



if __name__ == "__main__":
    main()
