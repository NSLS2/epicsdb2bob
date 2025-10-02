from phoebusgen.widget import (
    ActionButton,
    ChoiceButton,
    ComboBox,
    Label,
    TextEntry,
    TextUpdate,
)
from phoebusgen.widget.widget import _Widget as Widget

Palette = dict[str, dict[type[Widget], tuple[int, int, int]]]

BACKGROUND_COLOR = (187, 187, 187)
TITLE_BAR_COLOR = (218, 218, 218)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

WIDGET_PALETTES: dict[str, Palette] = {
    "default": {
        "foreground": {
            TextUpdate: (10, 0, 184),
            ComboBox: BLACK,
            TextEntry: BLACK,
            ActionButton: BLACK,
            ChoiceButton: BLACK,
            Label: BLACK,
        },
        "background": {
            ComboBox: (115, 223, 255),
            TextEntry: (115, 223, 255),
            ActionButton: (115, 223, 255),
            ChoiceButton: (115, 223, 255),
            Label: BACKGROUND_COLOR,
        },
    }
}
