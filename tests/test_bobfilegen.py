import random

import pytest
from phoebusgen.widget import Label, Rectangle

from epicsdb2bob.bobfile_gen import (
    add_border,
    add_dividing_line,
    add_label_for_record,
    add_widget_for_record,
    generate_bobfile_for_db,
    get_height_width_of_bobfile,
    get_next_widget_position,
    get_next_x_position,
    get_widget_start_positions,
    template_to_bob,
)
from epicsdb2bob.config import (
    DEFAULT_RTYP_TO_WIDGET_MAP,
    TitleBarFormat,
)


def test_generate_bobfiles(db_with_readbacks, default_config):
    screen = generate_bobfile_for_db(
        "DB With Readbacks", db_with_readbacks, {}, default_config
    )
    screen.write_screen("tests/test_outputs/db_with_readbacks.bob")


def test_get_bobfile_height_width():
    height, width = get_height_width_of_bobfile(
        "tests/test_outputs/db_with_readbacks.bob"
    )
    assert height == 640
    assert width == 490


def test_template_to_bobfile_name():
    bobfile_name = template_to_bob("my_template.template")
    assert bobfile_name == "my_template.bob"


@pytest.mark.parametrize(
    "rtyp",
    [*DEFAULT_RTYP_TO_WIDGET_MAP.keys()],
)
def test_add_label_for_record(simple_record_factory, default_config, rtyp):
    record = simple_record_factory(rtyp, rtyp)
    start_x = random.randint(0, 500)
    start_y = random.randint(0, 500)
    label = add_label_for_record(record, start_x, start_y, default_config)
    print(label)
    expected_text = f"{record.name.upper()} desc"

    assert label.get_element_value("text") == expected_text
    assert int(label.get_element_value("width")) == default_config.default_widget_width
    assert (
        int(label.get_element_value("height")) == default_config.default_widget_height
    )
    assert int(label.get_element_value("x")) == start_x
    assert int(label.get_element_value("y")) == start_y
    assert int(label.get_element_value("horizontal_alignment")) == 0  # LEFT


@pytest.mark.parametrize(
    "rtyp",
    [*DEFAULT_RTYP_TO_WIDGET_MAP.keys()],
)
def test_add_widget_for_record(
    simple_record_factory, readback_record_factory, default_config, rtyp
):
    record = simple_record_factory(rtyp, rtyp)
    start_x = random.randint(0, 100)
    start_y = random.randint(0, 100)
    if rtyp.endswith("o") or rtyp.endswith("out"):
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
    assert label.get_element_value("text") == f"{record.name.upper()} desc"
    assert int(label.get_element_value("x")) == start_x
    assert int(label.get_element_value("y")) == start_y

    x_inc = default_config.default_widget_width + default_config.widget_offset

    main_widget = widget_list[1]
    assert isinstance(main_widget, DEFAULT_RTYP_TO_WIDGET_MAP[rtyp])
    assert main_widget.get_element_value("pv_name") == record.name
    assert int(main_widget.get_element_value("x")) == start_x + x_inc
    assert int(main_widget.get_element_value("y")) == start_y

    if readback:
        readback_widget = widget_list[2]
        assert isinstance(readback_widget, DEFAULT_RTYP_TO_WIDGET_MAP[readback.rtyp])
        assert readback_widget.get_element_value("pv_name") == readback.name
        assert int(readback_widget.get_element_value("x")) == start_x + 2 * x_inc
        assert int(readback_widget.get_element_value("y")) == start_y


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
        assert int(border.get_element_value("x")) == 0
        assert int(border.get_element_value("y")) == 11
        assert isinstance(border, Rectangle)
        assert int(border.get_element_value("line_width")) == 2
        assert border.get_element_value("transparent") == "true"


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
    assert int(dividing_line.get_element_value("x")) == 10
    assert int(dividing_line.get_element_value("y")) == 20
    assert isinstance(dividing_line, Rectangle)
    assert int(dividing_line.get_element_value("width")) == 2
    assert int(dividing_line.get_element_value("height")) == 1180


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
