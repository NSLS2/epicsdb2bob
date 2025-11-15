import copy

import pytest
from phoebusgen.widget import (
    ActionButton,
    ChoiceButton,
    ComboBox,
    Label,
    TextEntry,
    TextUpdate,
)
from phoebusgen.widget.widget import _Widget as Widget

from epicsdb2bob.palettes import BLACK, BUILTIN_PALETTES, WHITE, Palette

pytestmark = pytest.mark.parametrize("palette_name", BUILTIN_PALETTES.keys())


@pytest.mark.parametrize(
    "widget_type",
    [
        ActionButton,
        ChoiceButton,
        ComboBox,
        Label,
        TextEntry,
        TextUpdate,
    ],
)
def test_default_palette_values(palette_name: str, widget_type: type[Widget]) -> None:
    palette = Palette()
    assert palette.get_widget_fg(widget_type) == BLACK
    assert palette.get_widget_bg(widget_type) == WHITE
    assert palette.screen_bg == WHITE
    assert palette.border_color == BLACK
    assert palette.title_bar_bg == WHITE
    assert palette.title_bar_fg == BLACK


@pytest.mark.parametrize(
    "widget_type",
    [
        ActionButton,
        ChoiceButton,
        ComboBox,
        Label,
        TextEntry,
        TextUpdate,
    ],
)
def test_builtin_palettes_get_widget_fg(
    palette_name: str, widget_type: type[Widget]
) -> None:
    palette = BUILTIN_PALETTES[palette_name]
    fg_color = palette.get_widget_fg(widget_type)
    assert isinstance(fg_color, tuple)
    assert len(fg_color) == 3
    for component in fg_color:
        assert 0 <= component <= 255

    if widget_type not in palette.widget_fg:
        assert fg_color == BLACK
    else:
        assert fg_color == palette.widget_fg[widget_type]


@pytest.mark.parametrize(
    "widget_type",
    [
        ActionButton,
        ChoiceButton,
        ComboBox,
        Label,
        TextEntry,
        TextUpdate,
    ],
)
def test_builtin_palettes_get_widget_bg(
    palette_name: str, widget_type: type[Widget]
) -> None:
    palette = BUILTIN_PALETTES[palette_name]
    bg_color = palette.get_widget_bg(widget_type)
    assert isinstance(bg_color, tuple)
    assert len(bg_color) == 3
    for component in bg_color:
        assert 0 <= component <= 255

    if widget_type not in palette.widget_bg:
        assert bg_color == WHITE
    else:
        assert bg_color == palette.widget_bg[widget_type]


def test_palette_update(palette_name: str) -> None:
    original_palette = BUILTIN_PALETTES[palette_name]
    palette = copy.deepcopy(original_palette)
    new_palette = Palette(
        screen_bg=(100, 100, 100),
        border_color=(50, 50, 50),
        title_bar_bg=(150, 150, 150),
        title_bar_fg=(200, 200, 200),
        widget_fg={TextUpdate: (0, 0, 0)},
        widget_bg={TextUpdate: (255, 255, 255)},
    )
    palette.update(new_palette)

    assert palette.screen_bg == (100, 100, 100)
    assert palette.border_color == (50, 50, 50)
    assert palette.title_bar_bg == (150, 150, 150)
    assert palette.title_bar_fg == (200, 200, 200)
    assert palette.widget_fg[TextUpdate] == (0, 0, 0)
    assert palette.widget_bg[TextUpdate] == (255, 255, 255)
    assert palette.get_widget_bg(ComboBox) == original_palette.get_widget_bg(ComboBox)


def test_palette_update_from_dict(palette_name: str) -> None:
    original_palette = BUILTIN_PALETTES[palette_name]
    palette = copy.deepcopy(original_palette)
    update_dict = {
        "screen_bg": [120, 120, 120],
        "border_color": [60, 60, 60],
        "title_bar_bg": [160, 160, 160],
        "title_bar_fg": [210, 210, 210],
        "widget_fg": {"TextUpdate": [10, 10, 10]},
        "widget_bg": {"TextUpdate": [245, 245, 245]},
    }
    palette.update_from_dict(update_dict)

    assert palette.screen_bg == (120, 120, 120)
    assert palette.border_color == (60, 60, 60)
    assert palette.title_bar_bg == (160, 160, 160)
    assert palette.title_bar_fg == (210, 210, 210)
    assert palette.widget_fg[TextUpdate] == (10, 10, 10)
    assert palette.widget_bg[TextUpdate] == (245, 245, 245)
    assert palette.get_widget_fg(ComboBox) == original_palette.get_widget_fg(ComboBox)


@pytest.mark.parametrize("widget_color_setting", ["fg", "bg"])
def test_palette_update_from_dict_invalid_widget(
    palette_name: str, widget_color_setting: str
) -> None:
    palette = copy.deepcopy(BUILTIN_PALETTES[palette_name])
    update_dict = {
        f"widget_{widget_color_setting}": {"NonExistentWidget": [10, 10, 10]},
    }
    with pytest.raises(
        ValueError, match="Unknown widget type NonExistentWidget in palette."
    ):
        palette.update_from_dict(update_dict)


def test_palette_update_from_dict_partial(palette_name: str) -> None:
    original_palette = BUILTIN_PALETTES[palette_name]
    palette = copy.deepcopy(original_palette)
    update_dict = {
        "screen_bg": [130, 130, 130],
    }
    palette.update_from_dict(update_dict)

    assert palette.screen_bg == (130, 130, 130)
    assert palette.border_color == original_palette.border_color
    assert palette.title_bar_bg == original_palette.title_bar_bg
    assert palette.title_bar_fg == original_palette.title_bar_fg
    assert palette.widget_fg == original_palette.widget_fg
    assert palette.widget_bg == original_palette.widget_bg
