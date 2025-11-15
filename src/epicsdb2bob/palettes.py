from dataclasses import dataclass, field
from typing import Any

import phoebusgen.widget as phoebusgen_widget
from phoebusgen.widget import (
    ActionButton,
    ChoiceButton,
    ComboBox,
    Label,
    TextEntry,
    TextUpdate,
)
from phoebusgen.widget.widget import _Widget as Widget

Color = tuple[int, int, int]

# Some default colors
WHITE: Color = (255, 255, 255)
BLACK: Color = (0, 0, 0)


@dataclass(frozen=False)  # Don't freeze to allow updates from YAML
class Palette:
    screen_bg: Color = WHITE
    border_color: Color = BLACK
    title_bar_bg: Color = WHITE
    title_bar_fg: Color = BLACK
    widget_fg: dict[type[Widget], Color] = field(default_factory=dict)
    widget_bg: dict[type[Widget], Color] = field(default_factory=dict)

    def get_widget_fg(self, widget_type: type[Widget]) -> Color:
        return self.widget_fg.get(widget_type, BLACK)

    def get_widget_bg(self, widget_type: type[Widget]) -> Color:
        return self.widget_bg.get(widget_type, WHITE)

    def update(self, other: "Palette") -> None:
        self.screen_bg = other.screen_bg if other.screen_bg else self.screen_bg
        self.border_color = (
            other.border_color if other.border_color else self.border_color
        )
        self.title_bar_bg = (
            other.title_bar_bg if other.title_bar_bg else self.title_bar_bg
        )
        self.title_bar_fg = (
            other.title_bar_fg if other.title_bar_fg else self.title_bar_fg
        )
        self.widget_fg.update(other.widget_fg)
        self.widget_bg.update(other.widget_bg)

    def update_from_dict(self, source: dict[str, Any]) -> None:
        if "screen_bg" in source:
            self.screen_bg = tuple(source["screen_bg"])
        if "border_color" in source:
            self.border_color = tuple(source["border_color"])
        if "title_bar_bg" in source:
            self.title_bar_bg = tuple(source["title_bar_bg"])
        if "title_bar_fg" in source:
            self.title_bar_fg = tuple(source["title_bar_fg"])
        if "widget_fg" in source:
            for key, value in source["widget_fg"].items():
                if not hasattr(phoebusgen_widget, key):
                    raise ValueError(f"Unknown widget type {key} in palette.")
                widget_type = getattr(phoebusgen_widget, key)
                self.widget_fg[widget_type] = tuple(value)
        if "widget_bg" in source:
            for key, value in source["widget_bg"].items():
                if not hasattr(phoebusgen_widget, key):
                    raise ValueError(f"Unknown widget type {key} in palette.")
                widget_type = getattr(phoebusgen_widget, key)
                self.widget_bg[widget_type] = tuple(value)


BUILTIN_PALETTES: dict[str, Palette] = {
    "default": Palette(
        screen_bg=(187, 187, 187),
        border_color=BLACK,
        title_bar_bg=(218, 218, 218),
        title_bar_fg=BLACK,
        widget_fg={
            TextUpdate: (10, 0, 184),
        },
        widget_bg={
            ComboBox: (115, 223, 255),
            TextEntry: (115, 223, 255),
            TextUpdate: (187, 187, 187),
            ActionButton: (115, 223, 255),
            ChoiceButton: (115, 223, 255),
            Label: (187, 187, 187),
        },
    ),
    "nsls2": Palette(
        screen_bg=WHITE,
        border_color=(43, 118, 255),
        title_bar_bg=(43, 118, 255),
        title_bar_fg=WHITE,
        widget_bg={
            ComboBox: (240, 240, 240),
            ActionButton: (240, 240, 240),
            ChoiceButton: (240, 240, 240),
        },
    ),
}
