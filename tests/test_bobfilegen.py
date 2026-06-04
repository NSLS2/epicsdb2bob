import os
import random
from pathlib import Path

import pytest
from phoebusgen.v4.widgets import Label, Rectangle
from phoebusgen.v4.properties import HorizontalAlignment as PGHorizontalAlignment

from epicsdb2bob.bobfile_gen import (
    add_border,
    add_dividing_line,
    add_label_for_record,
    add_widget_for_record,
    generate_bobfile_for_db,
    generate_bobfile_for_substitution,
    get_height_width_of_bobfile,
    get_next_widget_position,
    get_next_x_position,
    get_widget_start_positions,
    template_to_bob,
)
from epicsdb2bob.config import (
    DEFAULT_RTYPE_TO_WIDGET_MAP,
    EmbedLevel,
    HorizontalAlignment,
    TitleBarFormat,
)
from epicsdb2bob.utils import (
    find_bobfiles_in_search_path,
    find_epics_dbs_and_templates,
    find_epics_subs,
)


def test_generate_bobfiles(db_with_readbacks, default_config, tmp_path):
    screen = generate_bobfile_for_db(
        "db_with_readbacks", db_with_readbacks, {}, default_config
    )
    screen.write_screen(tmp_path / "db_with_readbacks.bob")

    with open(tmp_path / "db_with_readbacks.bob") as f:
        gen_bobfile_content = f.read()

    with open("tests/outputs/db_with_readbacks.bob") as f:
        expected_bobfile_content = f.read()

    assert gen_bobfile_content == expected_bobfile_content


def test_get_bobfile_height_width():
    height, width = get_height_width_of_bobfile("tests/outputs/db_with_readbacks.bob")
    assert height == 640
    assert width == 510


def test_template_to_bobfile_name():
    bobfile_name = template_to_bob("my_template.template")
    assert bobfile_name == "my_template.bob"


@pytest.mark.parametrize(
    "alignment,expected",
    [
        (HorizontalAlignment.LEFT, PGHorizontalAlignment.LEFT),
        (HorizontalAlignment.CENTER, PGHorizontalAlignment.CENTER),
        (HorizontalAlignment.RIGHT, PGHorizontalAlignment.RIGHT),
    ],
)
def test_align_widget_horizontally(simple_label, alignment, expected):
    simple_label.horizontal_alignment = PGHorizontalAlignment(alignment)
    assert simple_label.horizontal_alignment == expected


@pytest.mark.parametrize(
    "rtype",
    [*DEFAULT_RTYPE_TO_WIDGET_MAP.keys()],
)
def test_add_label_for_record(simple_record_factory, default_config, rtype):
    record = simple_record_factory(rtype, rtype)
    start_x = random.randint(0, 500)
    start_y = random.randint(0, 500)
    label = add_label_for_record(record, start_x, start_y, default_config)
    print(label)
    expected_text = f"{record.name.upper()} desc"

    assert label.text == expected_text
    assert label.width == default_config.default_widget_width
    assert label.height == default_config.default_widget_height
    assert label.x == start_x
    assert label.y == start_y
    assert label.horizontal_alignment == PGHorizontalAlignment.LEFT


@pytest.mark.parametrize(
    "rtype",
    [*DEFAULT_RTYPE_TO_WIDGET_MAP.keys()],
)
def test_add_widget_for_record(
    simple_record_factory, readback_record_factory, default_config, rtype
):
    record = simple_record_factory(rtype, rtype)
    start_x = random.randint(0, 100)
    start_y = random.randint(0, 100)
    if rtype.endswith("o") or rtype.endswith("out"):
        readback = readback_record_factory(record)
    else:
        readback = None

    widget_list = add_widget_for_record(
        record, start_x, start_y, {}, default_config, readback_record=readback
    )

    if not readback:
        assert len(widget_list) == 2
    else:
        assert len(widget_list) == 3

    label = widget_list[0]
    assert isinstance(label, Label)
    assert label.text == f"{record.name.upper()} desc"
    assert label.x == start_x
    assert label.y == start_y

    x_inc = default_config.default_widget_width + default_config.widget_offset

    main_widget = widget_list[1]
    assert isinstance(main_widget, DEFAULT_RTYPE_TO_WIDGET_MAP[rtype])
    assert main_widget.pv_name == record.name
    assert main_widget.x == start_x + x_inc
    assert main_widget.y == start_y

    if readback:
        readback_widget = widget_list[2]
        assert isinstance(readback_widget, DEFAULT_RTYPE_TO_WIDGET_MAP[readback.rtype])
        assert readback_widget.pv_name == readback.name
        assert readback_widget.x == start_x + 2 * x_inc
        assert readback_widget.y == start_y


@pytest.mark.parametrize(
    "title_bar_format",
    [
        TitleBarFormat("none"),
        TitleBarFormat("minimal"),
        TitleBarFormat("full"),
    ],
)
def test_add_border(default_config, title_bar_format):
    default_config.title_bar_format = title_bar_format
    border = add_border(default_config)

    if title_bar_format != TitleBarFormat.MINIMAL:
        assert border is None
    else:
        assert border is not None
        assert border.x == 0
        assert border.y == 11
        assert isinstance(border, Rectangle)
        assert border.line_width == 2
        assert border.transparent is True


@pytest.mark.parametrize(
    "title_bar_format",
    [
        TitleBarFormat("none"),
        TitleBarFormat("minimal"),
        TitleBarFormat("full"),
    ],
)
def test_get_widget_start_positions(default_config, title_bar_format):
    default_config.title_bar_format = title_bar_format
    start_x, start_y = get_widget_start_positions(default_config)
    assert start_x == 10
    if title_bar_format == TitleBarFormat.NONE:
        assert start_y == 10
    elif title_bar_format == TitleBarFormat.MINIMAL:
        assert start_y == 30
    elif title_bar_format == TitleBarFormat.FULL:
        assert start_y == 50


def test_add_dividing_line(default_config):
    dividing_line = add_dividing_line(10, 20, default_config)
    assert dividing_line is not None
    assert dividing_line.x == 10
    assert dividing_line.y == 20
    assert isinstance(dividing_line, Rectangle)
    assert dividing_line.width == 2
    assert dividing_line.height == 1180


@pytest.mark.parametrize(
    "current_x, col_width_widgets, expected_x",
    [
        (10, 2, 330),  # start position, col w/ 2 widgets -> 10 + 2 * (150 + 10) = 330
        (330, 3, 810),  # previous + col w/ 3 widgets -> 330 + 3 * (150 + 10) = 810
        (810, 3, 1290),  # previous + col w/ 3 widgets -> 810 + 3 * (150 + 10) = 1290
    ],
)
def test_get_next_x_position(default_config, current_x, col_width_widgets, expected_x):
    new_x = get_next_x_position(current_x, col_width_widgets, default_config)
    assert new_x == expected_x


@pytest.mark.parametrize(
    "current_x, current_y, col_width_widgets, expected_x, expected_y",
    [
        (10, 30, 2, 10, 60),  # start position
        (10, 60, 2, 10, 90),  # same col
        (10, 1190, 2, 330, 30),  # hit max height, next col
        (330, 30, 3, 330, 60),  # new col
        (330, 60, 3, 330, 90),  # same col
        (330, 1190, 3, 810, 30),  # hit max height, next col
    ],
)
def test_get_next_widget_position(
    default_config, current_x, current_y, col_width_widgets, expected_x, expected_y
):
    new_x, new_y = get_next_widget_position(
        current_x, current_y, col_width_widgets, default_config
    )
    assert new_x == expected_x
    assert new_y == expected_y


def test_generate_bobfile_for_substitutions(tmp_path, default_config):
    default_config.embed = EmbedLevel.ALL
    input_file_path = Path("tests") / "inputs"

    written_bobfiles: dict[str, Path] = find_bobfiles_in_search_path(
        default_config.bobfile_search_path
    )

    databases = find_epics_dbs_and_templates(input_file_path, {})
    for name in databases:
        screen = generate_bobfile_for_db(name, databases[name], {}, default_config)

        full_output_path = os.path.join(tmp_path, f"{name}.bob")
        screen.write_screen(full_output_path)
        written_bobfiles[os.path.basename(full_output_path)] = Path(full_output_path)

    name, substitution = list(find_epics_subs(input_file_path).items())[0]
    screen = generate_bobfile_for_substitution(
        name,
        substitution,
        written_bobfiles,
        default_config,
    )
    full_output_path = os.path.join(tmp_path, f"{name}.bob")
    screen.write_screen(full_output_path)
    written_bobfiles[os.path.basename(full_output_path)] = Path(full_output_path)

    with open(full_output_path) as f:
        gen_bobfile_content = f.read()

    with open("tests/outputs/example_sub.bob") as f:
        expected_bobfile_content = f.read()

    assert gen_bobfile_content == expected_bobfile_content
