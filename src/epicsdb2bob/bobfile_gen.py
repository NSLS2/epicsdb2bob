import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree as ET

from dbtoolspy import Database, Record
from phoebusgen.screen import Screen
from phoebusgen.widget import (
    ActionButton,
    EmbeddedDisplay,
    Label,
    Rectangle,
)
from phoebusgen.widget.properties import (
    _BackgroundColor as HasBackgroundColor,
)
from phoebusgen.widget.properties import (
    _Font as HasFontSize,
)
from phoebusgen.widget.properties import (
    _ForegroundColor as HasForegroundColor,
)
from phoebusgen.widget.widget import _Widget as Widget

from .config import EmbedLevel, EPICSDB2BOBConfig, MacroSetLevel, TitleBarFormat
from .palettes import BACKGROUND_COLOR, BLACK, WHITE

logger = logging.getLogger("epicsdb2bob")


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


def add_label_for_record(
    record: Record, start_x: int, start_y: int, config: EPICSDB2BOBConfig
) -> Label:
    description = record.fields.get("DESC", record.name.rsplit(")")[-1])  #  type: ignore
    label = Label(
        short_uuid(),
        description,
        start_x,
        start_y,
        config.default_widget_width,
        config.default_widget_height,
    )

    label.foreground_color(*config.palette["foreground"].get(Label, BLACK))
    label.background_color(*config.palette["background"].get(Label, BACKGROUND_COLOR))
    label.font_size(config.font_size)

    return label


def add_widget_for_record(
    record: Record,
    start_x: int,
    start_y: int,
    config: EPICSDB2BOBConfig,
    readback_record: Record | None = None,
    with_label: bool = True,
) -> list[Widget]:
    widget_type = config.rtyp_to_widget_map[str(record.rtyp)]

    widgets_to_add: list[Widget] = []
    current_x = start_x

    if with_label:
        widgets_to_add.append(add_label_for_record(record, start_x, start_y, config))
        current_x += (
            config.widget_widths.get(Label, config.default_widget_width)
            + config.widget_offset
        )

    pv_name = record.name if record.name is not None else ""
    if config.macro_set_level != MacroSetLevel.WIDGET:
        for macro_name, macro_value in config.macros.items():
            pv_name = pv_name.replace(macro_value, f"$({macro_name})")

    widget = widget_type(
        short_uuid(),
        str(pv_name),
        current_x,
        start_y,
        config.widget_widths.get(widget_type, config.default_widget_width),
        config.default_widget_height,
    )

    if isinstance(widget, HasForegroundColor):
        widget.foreground_color(*config.palette["foreground"].get(widget_type, BLACK))

    if isinstance(widget, HasBackgroundColor):
        widget.background_color(
            *config.palette["background"].get(widget_type, BACKGROUND_COLOR)
        )

    if isinstance(widget, HasFontSize):
        widget.font_size(config.font_size)

    widgets_to_add.append(widget)
    current_x += (
        config.widget_widths.get(widget_type, config.default_widget_width)
        + config.widget_offset
    )

    if readback_record:
        widgets_to_add.extend(
            add_widget_for_record(
                readback_record,
                current_x,
                start_y,
                config,
                with_label=False,
            )
        )

    return widgets_to_add


def add_title_bar(
    name: str, screen: Screen, config: EPICSDB2BOBConfig, title_bar_width: int
) -> None:
    if config.title_bar_format == TitleBarFormat.NONE:
        return

    title_bar = Label(
        short_uuid(),
        name,
        config.widget_offset
        if config.title_bar_format == TitleBarFormat.MINIMAL
        else 0,
        0,
        title_bar_width,
        config.title_bar_heights[config.title_bar_format],
    )
    title_bar.foreground_color(*WHITE)
    if config.title_bar_format == TitleBarFormat.FULL:
        title_bar.font_size(config.font_size * 2)
        title_bar.horizontal_alignment_center()
    elif config.title_bar_format in [
        TitleBarFormat.MINIMAL,
        TitleBarFormat.MINIMAL_CENTERED,
    ]:
        title_bar.auto_size()
        title_bar.font_size(config.font_size + 2)
        title_bar.border_width(2)
        title_bar.border_color(*BLACK)

    title_bar.background_color(*config.title_bar_color)
    title_bar.transparent(False)
    title_bar.vertical_alignment_middle()
    screen.add_widget(title_bar)


def add_border(screen: Screen, config: EPICSDB2BOBConfig) -> Rectangle:
    border = Rectangle(
        short_uuid(),
        0,
        int(config.title_bar_heights[config.title_bar_format] / 2) + 1,
        0,
        0,
    )
    border.transparent(True)
    border.line_width(2)
    border.line_color(*BLACK)
    if config.title_bar_format == TitleBarFormat.MINIMAL:
        screen.add_widget(border)

    return border


def generate_bobfile_for_db(
    name: str, database: Database, config: EPICSDB2BOBConfig
) -> Screen:
    screen = Screen(name)

    current_x_pos = config.widget_offset
    current_y_pos = (
        2 * config.widget_offset + config.title_bar_heights[config.title_bar_format]
    )
    hit_max_y_pos = False
    max_widgets_in_row = 2

    border = add_border(screen, config)

    records_seen = []

    for record in database.values():
        logger.info(f"Processing record: {record.name} of type {record.rtyp}")
        if record.rtyp not in config.rtyp_to_widget_map:
            logger.warning(f"Record type {record.rtyp} not supported, skipping.")
        else:
            if record.name in records_seen:
                logger.info(f"Record {record.name} already processed, skipping.")
            else:
                readback_record = None
                if record.name + config.readback_suffix in database:
                    rb = database[record.name + config.readback_suffix]
                    if rb.rtyp in config.rtyp_to_widget_map:
                        readback_record = rb
                        logger.info(f"Found readback record: {rb.name}")
                        max_widgets_in_row = 3

                for widget in add_widget_for_record(
                    record, current_x_pos, current_y_pos, config
                ):
                    logger.info(
                        f"Adding {widget.__class__.__name__} widget for {record.name}"
                    )
                    logger.debug(f"Position: ({current_x_pos}, {current_y_pos})")
                    screen.add_widget(widget)

                records_seen.append(record.name)
                if readback_record:
                    records_seen.append(readback_record.name)

                current_y_pos += config.default_widget_height + config.widget_offset
                if (
                    current_y_pos
                    > config.max_screen_height
                    - config.title_bar_heights[config.title_bar_format]
                ):
                    hit_max_y_pos = True
                    dividing_line = Rectangle(
                        short_uuid(),
                        current_x_pos
                        + max_widgets_in_row
                        * (config.default_widget_width + config.widget_offset),
                        config.widget_offset
                        + config.title_bar_heights[config.title_bar_format],
                        2,
                        config.max_screen_height
                        - config.title_bar_heights[config.title_bar_format]
                        - config.widget_offset,
                    )
                    dividing_line.line_color(*BLACK)
                    screen.add_widget(dividing_line)

                    current_y_pos = (
                        2 * config.widget_offset
                        + config.title_bar_heights[config.title_bar_format]
                    )
                    current_x_pos += (
                        max_widgets_in_row
                        * (config.default_widget_width + config.widget_offset)
                        + config.widget_offset
                    )
                    max_widgets_in_row = 2

    screen_width = current_x_pos + max_widgets_in_row * (
        config.default_widget_width + config.widget_offset
    )
    if hit_max_y_pos:
        screen_height = config.max_screen_height + config.widget_offset
    else:
        screen_height = current_y_pos + config.widget_offset

    add_title_bar(name, screen, config, screen_width - config.widget_offset)

    if config.title_bar_format == "minimal":
        border.width(screen_width)
        border.height(
            screen_height - int(config.title_bar_heights[config.title_bar_format] / 2)
        )

    screen.background_color(*config.background_color)

    screen.height(screen_height)
    screen.width(screen_width)

    return screen


def get_height_width_of_bobfile(
    bobfile_path: str | Path, config: EPICSDB2BOBConfig
) -> tuple[int, int]:
    with open(bobfile_path) as bobfile:
        xml = ET.parse(bobfile)

        height = int(xml.getroot().find("height").text) + config.widget_offsetoffset  # type: ignore
        width = int(xml.getroot().find("width").text) + config.widget_offsetoffset  # type: ignore
        return height, width


def generate_bobfile_for_substitution(
    substitution_name: str,
    substitution: dict[str, Any],
    found_bobfiles: dict[str, Path],
    config: EPICSDB2BOBConfig,
) -> Screen:
    """
    Generate a BOB file for a substitution.
    """
    screen = Screen(substitution_name)
    screen.background_color(*config.background_color)

    screen_width = 0
    max_col_width = 0
    hit_max_y_pos = False

    current_x_pos = config.widget_offset
    current_y_pos = (
        config.widget_offset + config.title_bar_heights[config.title_bar_format]
    )
    launcher_buttons: dict[str, ActionButton] = {}

    logger.info(f"Generating screen for substitution: {substitution_name}")
    logger.debug(f"Found bobfiles: {found_bobfiles}")

    for template in substitution:
        template_instances = substitution[template]
        logger.info(f"Processing template: {template}")
        for i, instance in enumerate(template_instances):
            if template_to_bob(template) in found_bobfiles and (
                config.embed == EmbedLevel.ALL
                or (config.embed == EmbedLevel.SINGLE and len(template_instances) == 1)
            ):
                logger.info(f"Embedding display for instance: {instance}")
                embed_height, embed_width = get_height_width_of_bobfile(
                    found_bobfiles[template_to_bob(template)], config
                )
                if (
                    current_y_pos + embed_height
                    > config.max_screen_height
                    + config.title_bar_heights[TitleBarFormat.FULL]
                ):
                    current_y_pos = (
                        config.widget_offset
                        + config.title_bar_heights[TitleBarFormat.FULL]
                    )
                    current_x_pos += max_col_width + config.widget_offset
                    max_col_width = 0

                embedded_display = EmbeddedDisplay(
                    short_uuid(),
                    template_to_bob(template),
                    current_x_pos,
                    current_y_pos,
                    embed_width,
                    embed_height,
                )
                current_y_pos += embed_height + config.widget_offset

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
                    config.default_widget_width,
                    config.default_widget_height,
                )
                launcher_buttons[template].action_open_display(
                    template_to_bob(template),
                    "tab",
                    f"{os.path.splitext(template)[0]} {i + 1}",
                    instance,
                )
                screen.add_widget(launcher_buttons[template])
                current_y_pos += config.default_widget_height + config.widget_offset

                if config.default_widget_width > max_col_width:
                    max_col_width = config.default_widget_width

                if (
                    current_y_pos
                    > config.max_screen_height
                    + config.title_bar_heights[TitleBarFormat.FULL]
                ):
                    hit_max_y_pos = True
                    current_y_pos = (
                        config.widget_offset
                        + config.title_bar_heights[TitleBarFormat.FULL]
                    )
                    current_x_pos += max_col_width + config.widget_offset
                    max_col_width = 0

    screen_height = current_y_pos + config.widget_offset
    if hit_max_y_pos:
        screen_height = config.max_screen_height + config.widget_offset
    screen_width = current_x_pos + max_col_width + config.widget_offset

    add_title_bar(
        substitution_name,
        screen,
        config,
        screen_width - config.widget_offset,
    )

    screen.height(screen_height)
    screen.width(screen_width)

    return screen
