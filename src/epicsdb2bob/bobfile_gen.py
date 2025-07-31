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


WIDGET_TO_RECORD_TYPE_MAP = {
    "mbbo": ComboBox,
    "mbbi": TextUpdate,
    "bo": ChoiceButton,
    "bi": LED,
    "ao": TextEntry,
    "ai": TextUpdate,
    "stringout": TextEntry,
    "stringin": TextUpdate,
}

WIDGET_WIDTHS = {
    LED: 20,
}


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


def add_widget_for_record(
    record: Record,
    start_x: int,
    start_y: int,
    readback_record: Record | None = None,
    with_label: bool = True,
) -> list[Any]:
    widget_type = WIDGET_TO_RECORD_TYPE_MAP[str(record.rtyp)]
    widgets_to_add: list[Any] = []
    current_x = start_x

    if with_label:
        widgets_to_add.append(add_label_for_record(record, start_x, start_y))
        current_x += DEFAULT_WIDGET_WIDTH + OFFSET

    widgets_to_add.append(
        widget_type(
            short_uuid(),
            str(record.name),
            current_x,
            start_y,
            WIDGET_WIDTHS.get(widget_type, DEFAULT_WIDGET_WIDTH),
            DEFAULT_WIDGET_HEIGHT,
        )
    )
    current_x += DEFAULT_WIDGET_WIDTH + OFFSET

    if readback_record:
        widgets_to_add.extend(
            add_widget_for_record(readback_record, current_x, start_y, with_label=False)
        )

    return widgets_to_add


def generate_bobfile_for_db(
    name: str, database: Database, title_bar_size: str, readback_suffix: str
) -> phoebusgen.screen.Screen:
    screen = phoebusgen.screen.Screen(name)

    current_x_pos = OFFSET
    current_y_pos = 2 * OFFSET + TITLE_BAR_HEIGHTS[title_bar_size]
    hit_max_y_pos = False
    max_widgets_in_row = 2

    border = Rectangle(
        short_uuid(), 0, int(TITLE_BAR_HEIGHTS[title_bar_size] / 2) + 1, 0, 0
    )
    border.transparent(True)
    border.line_width(2)
    border.line_color(0, 0, 0)
    if title_bar_size == "minimal":
        screen.add_widget(border)

    records_seen = []

    for record in database.values():
        logger.info(f"Processing record: {record.name} of type {record.rtyp}")
        if record.rtyp not in WIDGET_TO_RECORD_TYPE_MAP:
            logger.warning(f"Record type {record.rtyp} not supported, skipping.")
        else:
            if record.name in records_seen:
                logger.info(f"Record {record.name} already processed, skipping.")
            else:
                readback_record = None
                if record.name + readback_suffix in database:
                    rb = database[record.name + readback_suffix]
                    if rb.rtyp in WIDGET_TO_RECORD_TYPE_MAP:
                        readback_record = rb
                        logger.info(f"Found readback record: {rb.name}")
                        max_widgets_in_row = 3

                for widget in add_widget_for_record(
                    record, current_x_pos, current_y_pos, readback_record
                ):
                    logger.info(
                        f"Adding {widget.__class__.__name__} widget for {record.name}"
                    )
                    logger.debug(f"Position: ({current_x_pos}, {current_y_pos})")
                    screen.add_widget(widget)

                records_seen.append(record.name)
                if readback_record:
                    records_seen.append(readback_record.name)

                current_y_pos += DEFAULT_WIDGET_HEIGHT + OFFSET
                if current_y_pos > MAX_HEIGHT - TITLE_BAR_HEIGHTS[title_bar_size]:
                    hit_max_y_pos = True
                    dividing_line = Rectangle(
                        short_uuid(),
                        current_x_pos
                        + max_widgets_in_row * (DEFAULT_WIDGET_WIDTH + OFFSET),
                        OFFSET + TITLE_BAR_HEIGHTS[title_bar_size],
                        2,
                        MAX_HEIGHT - TITLE_BAR_HEIGHTS[title_bar_size] - OFFSET,
                    )
                    dividing_line.line_color(0, 0, 0)
                    screen.add_widget(dividing_line)

                    current_y_pos = 2 * OFFSET + TITLE_BAR_HEIGHTS[title_bar_size]
                    current_x_pos += (
                        max_widgets_in_row * (DEFAULT_WIDGET_WIDTH + OFFSET) + OFFSET
                    )
                    max_widgets_in_row = 2

    screen_width = current_x_pos + max_widgets_in_row * (DEFAULT_WIDGET_WIDTH + OFFSET)
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

            border.width(screen_width)
            border.height(screen_height - int(TITLE_BAR_HEIGHTS[title_bar_size] / 2))

        title_bar.background_color(100, 100, 100)
        title_bar.transparent(False)
        title_bar.vertical_alignment_middle()
        screen.add_widget(title_bar)

    screen.background_color(179, 179, 179)

    screen.height(screen_height)
    screen.width(screen_width)

    return screen
