import logging
from typing import Any
from uuid import uuid4

import phoebusgen
import phoebusgen.screen
from dbtoolspy import Database, Record
from phoebusgen.widget import LED, ChoiceButton, Label, Rectangle, TextEntry, TextUpdate, ComboBox

logger = logging.getLogger("epicsdb2bob")

MAX_HEIGHT = 1200
OFFSET = 10

TITLE_BAR_HEIGHT = 50

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


def generate_bobfile_for_db(name: str, database: Database) -> phoebusgen.screen.Screen:
    screen = phoebusgen.screen.Screen(name)

    current_x_pos = OFFSET
    current_y_pos = 2 * OFFSET + TITLE_BAR_HEIGHT

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
                if current_y_pos > MAX_HEIGHT - TITLE_BAR_HEIGHT:
                    screen.add_widget(
                        Rectangle(
                            short_uuid(),
                            current_x_pos + 2 * (DEFAULT_WIDGET_WIDTH + OFFSET),
                            OFFSET + TITLE_BAR_HEIGHT,
                            2,
                            MAX_HEIGHT - TITLE_BAR_HEIGHT - OFFSET,
                        )
                    )
                    current_y_pos = 2 * OFFSET + TITLE_BAR_HEIGHT
                    current_x_pos += 2 * (DEFAULT_WIDGET_WIDTH + OFFSET) + OFFSET

    screen_width = current_x_pos + 2* (DEFAULT_WIDGET_WIDTH + OFFSET)
    screen_height = MAX_HEIGHT + OFFSET
    
    title_bar = Rectangle(
        short_uuid(),
        0,
        0,
        screen_width,
        TITLE_BAR_HEIGHT,
    )
    screen.add_widget(title_bar)

    title = Label(
        short_uuid(),
        name,
        0,
        0,
        screen_width,
        TITLE_BAR_HEIGHT,
    )
    title.foreground_color(255,255,255)
    title.font_size(32)
    title.horizontal_alignment_center()
    title.vertical_alignment_middle()
    screen.add_widget(title)

    screen.height(screen_height)
    screen.width(screen_width)

    return screen
