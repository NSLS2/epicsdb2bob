import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree as ET

import phoebusgen
import phoebusgen.screen
from dbtoolspy import Database, Record
from phoebusgen.widget import (
    LED,
    ActionButton,
    ChoiceButton,
    ComboBox,
    EmbeddedDisplay,
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

DEFAULT_BACKGROUND_COLOR = (179, 179, 179)
DEFAULT_TITLE_BAR_COLOR = (100, 100, 100)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


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


def template_to_bob(template: str) -> str:
    """
    Convert a template file name to a BOB file name.
    """
    return os.path.splitext(os.path.basename(template))[0] + ".bob"


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


def add_title_bar(screen, title_bar_size: str, name: str, title_bar_width: int) -> None:
    if title_bar_size == "none":
        return

    title_bar = Label(
        short_uuid(),
        name,
        OFFSET if title_bar_size == "minimal" else 0,
        0,
        title_bar_width,
        TITLE_BAR_HEIGHTS[title_bar_size],
    )
    title_bar.foreground_color(*WHITE)
    if title_bar_size == "full":
        title_bar.font_size(32)
        title_bar.horizontal_alignment_center()
    elif title_bar_size == "minimal":
        title_bar.auto_size()
        title_bar.font_size(18)
        title_bar.border_width(2)
        title_bar.border_color(*BLACK)

    title_bar.background_color(*DEFAULT_TITLE_BAR_COLOR)
    title_bar.transparent(False)
    title_bar.vertical_alignment_middle()
    screen.add_widget(title_bar)


def add_border(screen, title_bar_size: str) -> Rectangle:
    border = Rectangle(
        short_uuid(), 0, int(TITLE_BAR_HEIGHTS[title_bar_size] / 2) + 1, 0, 0
    )
    border.transparent(True)
    border.line_width(2)
    border.line_color(*BLACK)
    if title_bar_size == "minimal":
        screen.add_widget(border)

    return border


def generate_bobfile_for_db(
    name: str, database: Database, title_bar_size: str, readback_suffix: str
) -> phoebusgen.screen.Screen:
    screen = phoebusgen.screen.Screen(name)

    current_x_pos = OFFSET
    current_y_pos = 2 * OFFSET + TITLE_BAR_HEIGHTS[title_bar_size]
    hit_max_y_pos = False
    max_widgets_in_row = 2

    border = add_border(screen, title_bar_size)

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
                    dividing_line.line_color(*BLACK)
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

    add_title_bar(screen, title_bar_size, name, screen_width - OFFSET)

    if title_bar_size == "minimal":
        border.width(screen_width)
        border.height(screen_height - int(TITLE_BAR_HEIGHTS[title_bar_size] / 2))

    screen.background_color(*DEFAULT_BACKGROUND_COLOR)

    screen.height(screen_height)
    screen.width(screen_width)

    return screen


def get_height_width_of_bobfile(bobfile_path: str | Path) -> tuple[int, int]:
    with open(bobfile_path) as bobfile:
        xml = ET.parse(bobfile)

        height = int(xml.getroot().find("height").text) + OFFSET
        width = int(xml.getroot().find("width").text) + OFFSET
        return height, width


def generate_bobfile_for_substitution(
    substitution_name: str,
    substitution: dict[str, Any],
    written_bobfiles: dict[str, str],
    embed: str = "none",
) -> phoebusgen.screen.Screen:
    """
    Generate a BOB file for a substitution.
    """
    screen = phoebusgen.screen.Screen(substitution_name)
    screen.background_color(*DEFAULT_BACKGROUND_COLOR)

    screen_width = 0
    max_col_width = 0
    hit_max_y_pos = False

    current_x_pos = OFFSET
    current_y_pos = OFFSET + TITLE_BAR_HEIGHTS["full"]
    launcher_buttons: dict[str, ActionButton] = {}

    logger.info(f"Generating screen for substitution: {substitution_name}")
    logger.debug(f"Found bobfiles: {written_bobfiles}")

    for template in substitution:
        template_instances = substitution[template]
        logger.info(f"Processing template: {template}")
        for i, instance in enumerate(template_instances):
            if template_to_bob(template) in written_bobfiles and (
                embed == "all" or (embed == "single" and len(template_instances) == 1)
            ):
                logger.info(f"Embedding display for instance: {instance}")
                embed_height, embed_width = get_height_width_of_bobfile(
                    written_bobfiles[template_to_bob(template)]
                )
                if (
                    current_y_pos + embed_height
                    > MAX_HEIGHT + TITLE_BAR_HEIGHTS["full"]
                ):
                    current_y_pos = OFFSET + TITLE_BAR_HEIGHTS["full"]
                    current_x_pos += max_col_width + OFFSET
                    max_col_width = 0

                embedded_display = EmbeddedDisplay(
                    short_uuid(),
                    template_to_bob(template),
                    current_x_pos,
                    current_y_pos,
                    embed_width,
                    embed_height,
                )
                current_y_pos += embed_height + OFFSET

                if embed_width > max_col_width:
                    max_col_width = embed_width
                for macro in instance:
                    embedded_display.macro(macro, instance[macro])
                screen.add_widget(embedded_display)

            elif template in launcher_buttons:
                launcher_buttons[template].action_open_display(
                    template_to_bob(template),
                    "tab",
                    f"{os.path.splitext(template)[0]} {i + 1}",
                    instance,
                )
            else:
                logger.info(f"Creating launcher button for template: {template}")
                launcher_buttons[template] = ActionButton(
                    short_uuid(),
                    os.path.splitext(template)[0],
                    "",
                    current_x_pos,
                    current_y_pos,
                    DEFAULT_WIDGET_WIDTH,
                    DEFAULT_WIDGET_HEIGHT,
                )
                launcher_buttons[template].action_open_display(
                    template_to_bob(template),
                    "tab",
                    f"{os.path.splitext(template)[0]} {i + 1}",
                    instance,
                )
                screen.add_widget(launcher_buttons[template])
                current_y_pos += DEFAULT_WIDGET_HEIGHT + OFFSET

                if DEFAULT_WIDGET_WIDTH > max_col_width:
                    max_col_width = DEFAULT_WIDGET_WIDTH

                if current_y_pos > MAX_HEIGHT + TITLE_BAR_HEIGHTS["full"]:
                    hit_max_y_pos = True
                    current_y_pos = OFFSET + TITLE_BAR_HEIGHTS["full"]
                    current_x_pos += max_col_width + OFFSET
                    max_col_width = 0

    screen_height = current_y_pos + OFFSET
    if hit_max_y_pos:
        screen_height = MAX_HEIGHT + OFFSET
    screen_width = current_x_pos + max_col_width + OFFSET

    add_title_bar(
        screen,
        "full",
        substitution_name,
        screen_width - OFFSET,
    )

    screen.height(screen_height)
    screen.width(screen_width)

    return screen
