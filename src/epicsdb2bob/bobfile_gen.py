import logging
from typing import Any
from uuid import uuid4

import phoebusgen
import phoebusgen.screen
from dbtoolspy import Database, Record
from phoebusgen.widget import (
    LED,
    ChoiceButton,
    ComboBox,
    Label,
    Rectangle,
    TextEntry,
    TextUpdate,
)

logger = logging.getLogger("epicsdb2bob")

MAX_HEIGHT = 1200
OFFSET = 10

TITLE_BAR_HEIGHTS = {"none": 0, "minimal": 10, "full": 50}

DEFAULT_WIDGET_WIDTH = 150
DEFAULT_WIDGET_HEIGHT = 20


def short_uuid() -> str:
    """
    Generate a short UUID string.
    """
    return str(uuid4())[:8]


def add_label_for_record(record: Record, start_x: int, start_y: int) -> Label:
    description = record.fields.get("DESC", record.name.rsplit(")")[-1])  #  type: ignore
    return Label(
        short_uuid(),
        description,
        start_x,
        start_y,
        DEFAULT_WIDGET_WIDTH,
        DEFAULT_WIDGET_HEIGHT,
    )


def add_text_update_widget(record: Record, start_x: int, start_y: int) -> list[Any]:
    widgets_to_add: list[Any] = []
    widgets_to_add.append(add_label_for_record(record, start_x, start_y))

    current_x = start_x + DEFAULT_WIDGET_WIDTH + OFFSET
    current_y = start_y
    widgets_to_add.append(
        TextUpdate(
            short_uuid(),
            str(record.name),
            current_x,
            current_y,
            DEFAULT_WIDGET_WIDTH,
            DEFAULT_WIDGET_HEIGHT,
        )
    )
    return widgets_to_add


def add_led_widget(record: Record, start_x: int, start_y: int) -> list[Any]:
    widgets_to_add: list[Any] = []
    widgets_to_add.append(add_label_for_record(record, start_x, start_y))

    current_x = start_x + DEFAULT_WIDGET_WIDTH + OFFSET
    current_y = start_y
    widgets_to_add.append(
        LED(
            short_uuid(),
            str(record.name),
            current_x,
            current_y,
            20,
            DEFAULT_WIDGET_HEIGHT,
        )
    )
    return widgets_to_add


def add_text_entry_widget(record: Record, start_x: int, start_y: int) -> list[Any]:
    widgets_to_add: list[Any] = []
    widgets_to_add.append(add_label_for_record(record, start_x, start_y))

    current_x = start_x + DEFAULT_WIDGET_WIDTH + OFFSET
    current_y = start_y
    widgets_to_add.append(
        TextEntry(
            short_uuid(),
            str(record.name),
            current_x,
            current_y,
            DEFAULT_WIDGET_WIDTH,
            DEFAULT_WIDGET_HEIGHT,
        )
    )
    return widgets_to_add


def add_choice_button_widget(record: Record, start_x: int, start_y: int) -> list[Any]:
    widgets_to_add: list[Any] = []
    widgets_to_add.append(add_label_for_record(record, start_x, start_y))

    current_x = start_x + DEFAULT_WIDGET_WIDTH + OFFSET
    current_y = start_y
    widgets_to_add.append(
        ChoiceButton(
            short_uuid(),
            str(record.name),
            current_x,
            current_y,
            DEFAULT_WIDGET_WIDTH,
            DEFAULT_WIDGET_HEIGHT,
        )
    )
    return widgets_to_add


def add_combo_box_widget(record: Record, start_x: int, start_y: int) -> list[Any]:
    widgets_to_add: list[Any] = []
    widgets_to_add.append(add_label_for_record(record, start_x, start_y))

    current_x = start_x + DEFAULT_WIDGET_WIDTH + OFFSET
    current_y = start_y
    widgets_to_add.append(
        ComboBox(
            short_uuid(),
            str(record.name),
            current_x,
            current_y,
            DEFAULT_WIDGET_WIDTH,
            DEFAULT_WIDGET_HEIGHT,
        )
    )
    return widgets_to_add


def generate_bobfile_for_db(
    name: str, database: Database, title_bar_size: str
) -> phoebusgen.screen.Screen:
    screen = phoebusgen.screen.Screen(name)

    current_x_pos = OFFSET
    current_y_pos = 2 * OFFSET + TITLE_BAR_HEIGHTS[title_bar_size]
    hit_max_y_pos = False

    records_seen = []

    record_types_to_funcs = {
        "mbbo": add_combo_box_widget,
        "mbbi": add_text_update_widget,
        "bo": add_choice_button_widget,
        "bi": add_led_widget,
        "ao": add_text_entry_widget,
        "ai": add_text_update_widget,
        "stringout": add_text_entry_widget,
        "stringin": add_text_update_widget,
    }

    for record in database.values():
        logger.info(f"Processing record: {record.name} of type {record.rtyp}")
        if record.rtyp not in record_types_to_funcs:
            logger.warning(f"Record type {record.rtyp} not supported, skipping.")
        else:
            for widget in record_types_to_funcs[record.rtyp](
                record, current_x_pos, current_y_pos
            ):
                logger.info(
                    f"Adding {widget.__class__.__name__} widget for {record.name}"
                )
                screen.add_widget(widget)
                records_seen.append(record.name)
                current_y_pos += DEFAULT_WIDGET_HEIGHT
                if current_y_pos > MAX_HEIGHT - TITLE_BAR_HEIGHTS[title_bar_size]:
                    hit_max_y_pos = True
                    dividing_line = Rectangle(
                        short_uuid(),
                        current_x_pos + 2 * (DEFAULT_WIDGET_WIDTH + OFFSET),
                        OFFSET + TITLE_BAR_HEIGHTS[title_bar_size],
                        2,
                        MAX_HEIGHT - TITLE_BAR_HEIGHTS[title_bar_size] - OFFSET,
                    )
                    dividing_line.line_color(0, 0, 0)
                    screen.add_widget(dividing_line)
                    current_y_pos = 2 * OFFSET + TITLE_BAR_HEIGHTS[title_bar_size]
                    current_x_pos += 2 * (DEFAULT_WIDGET_WIDTH + OFFSET) + OFFSET

    screen_width = current_x_pos + 2 * (DEFAULT_WIDGET_WIDTH + OFFSET)
    if hit_max_y_pos:
        screen_height = MAX_HEIGHT + OFFSET
    else:
        screen_height = current_y_pos + OFFSET

    if title_bar_size != "none":
        title_bar = Label(
            short_uuid(),
            name,
            OFFSET,
            0,
            screen_width - OFFSET,
            TITLE_BAR_HEIGHTS[title_bar_size],
        )
        title_bar.foreground_color(255, 255, 255)
        if title_bar_size == "full":
            title_bar.font_size(32)
            title_bar.horizontal_alignment_center()
        elif title_bar_size == "minimal":
            title_bar.auto_size()
            title_bar.font_size(18)
            title_bar.border_width(2)
            title_bar.border_color(0, 0, 0)
            border = Rectangle(
                short_uuid(),
                0,
                int(TITLE_BAR_HEIGHTS[title_bar_size] / 2) + 1,
                screen_width,
                screen_height - int(TITLE_BAR_HEIGHTS[title_bar_size] / 2),
            )
            border.transparent(True)
            border.line_width(2)
            border.line_color(0, 0, 0)
            screen.add_widget(border)

        title_bar.background_color(100, 100, 100)
        title_bar.transparent(False)
        title_bar.vertical_alignment_middle()
        screen.add_widget(title_bar)

    screen.background_color(179, 179, 179)

    screen.height(screen_height)
    screen.width(screen_width)

    return screen
