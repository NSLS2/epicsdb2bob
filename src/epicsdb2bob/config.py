import os
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import yaml
from phoebusgen import widget as phoebusgen_widget
from phoebusgen.widget import LED, ChoiceButton, ComboBox, TextEntry, TextUpdate
from phoebusgen.widget.widget import _Widget as Widget

from .palettes import WIDGET_PALETTES, Palette


class EmbedLevel(str, Enum):
    """Determines whether multiple screens should be combined via embedding."""

    NONE = (
        "none"  # No embedding. Use top level screens with buttons to launch subscreens
    )
    SINGLE = "single"  # Embed subscreens provided there is one instance of each
    ALL = "all"  # Embed all subscreens, even if there are multiple instances of each


class TitleBarFormat(str, Enum):
    """Determines the format of the title bar."""

    NONE = "none"  # No title bar
    MINIMAL = "minimal"  # Minimal title bar
    MINIMAL_CENTERED = "minimal_centered"  # Minimal title bar, but centered
    FULL = "full"  # Full title bar


class MacroSetLevel(str, Enum):
    """Determines at what level macros should be set."""

    NONE = "none"  # No macros
    SCREEN = "screen"  # Set macros at the screen level
    WIDGET = "widget"  # Set macros at the widget level


DEFAULT_RTYP_TO_WIDGET_MAP: dict[str, type[Widget]] = {
    "mbbo": ComboBox,
    "mbbi": TextUpdate,
    "bo": ChoiceButton,
    "bi": LED,
    "ao": TextEntry,
    "ai": TextUpdate,
    "stringout": TextEntry,
    "stringin": TextUpdate,
}

@dataclass(frozen=False)
class EPICSDB2BOBConfig:
    debug: bool = False
    embed: EmbedLevel = EmbedLevel.SINGLE
    macro_set_level: MacroSetLevel = MacroSetLevel.SCREEN
    title_bar_format: TitleBarFormat = TitleBarFormat.MINIMAL
    rtyp_to_widget_map: dict[str, type[Widget]] = field(default_factory=lambda: DEFAULT_RTYP_TO_WIDGET_MAP)
    readback_suffix: str = "_RBV"
    bobfile_search_path: list[Path] = field(default_factory=list)
    palette: Palette = field(default_factory=lambda: WIDGET_PALETTES["default"])
    font_size: int = 16
    default_widget_width: int = 150
    default_widget_height: int = 20
    max_screen_height: int = 1200
    widget_offset: int = 10
    title_bar_heights: dict[TitleBarFormat, int] = field(default_factory=lambda: {
        TitleBarFormat.NONE: 0,
        TitleBarFormat.MINIMAL: 20,
        TitleBarFormat.MINIMAL_CENTERED: 20,
        TitleBarFormat.FULL: 40,
    })
    widget_widths: dict[type[Widget], int] = field(default_factory=lambda: {LED: 20})
    background_color: tuple[int, int, int] = (187, 187, 187)
    title_bar_color: tuple[int, int, int] = (218, 218, 218)

    @staticmethod
    def from_yaml(file_path: Path, cli_args: dict[str, Any]) -> "EPICSDB2BOBConfig":
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Config file {file_path} does not exist.")

        data = cli_args.copy()
        with open(file_path) as f:
            data.update(yaml.safe_load(f))


        rtyp_to_widget_map = DEFAULT_RTYP_TO_WIDGET_MAP.copy()
        if "rtyp_to_widget_map" in data:
            for key in data["rtyp_to_widget_map"]:
                rtyp_to_widget_map[key] = getattr(
                    phoebusgen_widget, data["rtyp_to_widget_map"][key]
                )

        widget_widths = {LED: 20}
        if "widget_widths" in data:
            for key in data["widget_widths"]:
                widget_widths[getattr(phoebusgen_widget, key)] = data["widget_widths"][
                    key
                ]

        # Get base builtin palette if set
        palette = WIDGET_PALETTES["default"]
        if "builtin_palette" in data and data["builtin_palette"] not in WIDGET_PALETTES:
            raise ValueError(
                f"Builtin palette {data['builtin_palette']} is not recognized."
                f"Valid options are: {list(WIDGET_PALETTES.keys())}"
            )
        elif "builtin_palette" in data:
            palette = WIDGET_PALETTES[data["builtin_palette"]]

        # Override with any custom palette settings
        custom_palette = {"foreground": {}, "background": {}}
        if "custom_palette" in data:
            for key in ["foreground", "background"]:
                for widget_type in data["custom_palette"][key]:
                    custom_palette[key][getattr(phoebusgen_widget, widget_type)] = data[
                        "custom_palette"
                    ][key][widget_type]

        palette["foreground"].update(custom_palette["foreground"])
        palette["background"].update(custom_palette["background"])

        return EPICSDB2BOBConfig(
            debug=data.get("debug", False),
            embed=EmbedLevel(data.get("embed", "single")),
            title_bar_format=TitleBarFormat(data.get("title_bar_format", "minimal")),
            readback_suffix=data.get("readback_suffix", "_RBV"),
            bobfile_search_path=[Path(p) for p in data.get("bobfile_search_path", [])],
            palette=palette,
            rtyp_to_widget_map=rtyp_to_widget_map,
            font_size=data.get("font_size", 16),
            default_widget_width=data.get("default_widget_width", 150),
            default_widget_height=data.get("default_widget_height", 20),
            max_screen_height=data.get("max_screen_height", 1200),
            widget_offset=data.get("widget_offset", 10),
            title_bar_heights={
                TitleBarFormat.NONE: data.get("title_bar_heights", {}).get("none", 0),
                TitleBarFormat.MINIMAL: data.get("title_bar_heights", {}).get(
                    "minimal", 20
                ),
                TitleBarFormat.MINIMAL_CENTERED: data.get("title_bar_heights", {}).get(
                    "minimal_centered", 20
                ),
                TitleBarFormat.FULL: data.get("title_bar_heights", {}).get("full", 40),
            },
            widget_widths={LED: data.get("widget_widths", {}).get("LED", 20)},
            background_color=tuple(data.get("background_color", (187, 187, 187))), #type: ignore
            title_bar_color=tuple(data.get("title_bar_color", (218, 218, 218))), #type: ignore
        )

    def __str__(self):
        return (
            f"EPICSDB2BOBConfig(debug={self.debug}, embed={self.embed}, "
            f"macro_set_level={self.macro_set_level}, "
            f"title_bar_format={self.title_bar_format}, "
            f"rtyp_to_widget_map={self.rtyp_to_widget_map}, "
            f"readback_suffix={self.readback_suffix}, "
            f"bobfile_search_path={self.bobfile_search_path}, "
            f"palette={self.palette}, font_size={self.font_size}, "
            f"default_widget_width={self.default_widget_width}, "
            f"default_widget_height={self.default_widget_height}, "
            f"max_screen_height={self.max_screen_height}, "
            f"widget_offset={self.widget_offset}, "
            f"title_bar_heights={self.title_bar_heights}, "
            f"widget_widths={self.widget_widths}, "
            f"background_color={self.background_color}, "
            f"title_bar_color={self.title_bar_color})"
        )