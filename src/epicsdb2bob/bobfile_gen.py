import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree as ET

from epicsdbtools import Database, Record
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
from phoebusgen.widget.properties import (
    _HorizontalAlignment as HasHorizontalAlignment,
)
from phoebusgen.widget.widget import _Widget as Widget

from .config import (
    EmbedLevel,
    EPICSDB2BOBConfig,
    HorizontalAlignment,
    MacroSetLevel,
    TitleBarFormat,
)
from .palettes import BLACK, WHITE

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


def align_widget_horizontally(
    widget: HasHorizontalAlignment, alignment: HorizontalAlignment
) -> None:
    if alignment == HorizontalAlignment.LEFT:
        widget.horizontal_alignment_left()
    elif alignment == HorizontalAlignment.CENTER:
        widget.horizontal_alignment_center()
    elif alignment == HorizontalAlignment.RIGHT:
        widget.horizontal_alignment_right()


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

    label.foreground_color(*config.palette.get_widget_fg(Label))
    label.background_color(*config.palette.get_widget_bg(Label))
    label.font_size(config.font_size)
    align_widget_horizontally(label, config.label_alignment)

    return label


def add_widget_for_record(
    record: Record,
    start_x: int,
    start_y: int,
    macros: dict[str, str],
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
        for macro_name, macro_value in macros.items():
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
        widget.foreground_color(*config.palette.get_widget_fg(widget_type))

    if isinstance(widget, HasBackgroundColor):
        widget.background_color(*config.palette.get_widget_bg(widget_type))

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
                macros,
                config,
                with_label=False,
            )
        )

    return widgets_to_add


def add_title_bar(
    name: str, config: EPICSDB2BOBConfig, title_bar_width: int
) -> Label | None:
    if config.title_bar_format == TitleBarFormat.NONE:
        return None

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
    elif config.title_bar_format == TitleBarFormat.MINIMAL:
        title_bar.auto_size()
        title_bar.font_size(config.font_size + 2)
        title_bar.border_width(2)
        title_bar.border_color(*BLACK)

    title_bar.background_color(*config.palette.title_bar_bg)
    title_bar.foreground_color(*config.palette.title_bar_fg)
    title_bar.transparent(False)
    title_bar.vertical_alignment_middle()
    return title_bar


def add_border(config: EPICSDB2BOBConfig) -> Rectangle | None:
    if config.title_bar_format != TitleBarFormat.MINIMAL:
        return None

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

    return border


def get_widget_start_positions(config: EPICSDB2BOBConfig) -> tuple[int, int]:
    start_x_pos = config.widget_offset
    start_y_pos = (
        config.widget_offset + config.title_bar_heights[config.title_bar_format]
    )
    return start_x_pos, start_y_pos


def get_next_x_position(
    current_x: int, col_width_widgets: int, config: EPICSDB2BOBConfig
) -> int:
    return current_x + col_width_widgets * (
        config.default_widget_width + config.widget_offset
    )


def get_next_widget_position(
    current_x, current_y: int, col_width_widgets: int, config: EPICSDB2BOBConfig
) -> tuple[int, int]:
    new_x = current_x
    new_y = current_y + config.default_widget_height + config.widget_offset

    # Reset to next column if we hit max height
    if (
        new_y
        > config.max_screen_height - config.title_bar_heights[config.title_bar_format]
    ):
        _, new_y = get_widget_start_positions(config)
        new_x = get_next_x_position(current_x, col_width_widgets, config)

    return new_x, new_y


def add_dividing_line(
    x_position: int,
    y_position: int,
    config: EPICSDB2BOBConfig,
) -> Rectangle:
    dividing_line = Rectangle(
        short_uuid(), x_position, y_position, 2, config.max_screen_height - y_position
    )
    dividing_line.line_color(*BLACK)
    return dividing_line


def generate_bobfile_for_db(
    name: str, database: Database, macros: dict[str, str], config: EPICSDB2BOBConfig
) -> Screen:
    screen = Screen(name)

    start_x_pos, start_y_pos = get_widget_start_positions(config)
    current_x_pos = start_x_pos
    current_y_pos = start_y_pos

    col_width_widgets = 2

    border = add_border(config)
    if border:
        screen.add_widget(border)

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

                widgets_for_record = add_widget_for_record(
                    record,
                    current_x_pos,
                    current_y_pos,
                    macros,
                    config,
                    readback_record=readback_record,
                )

                col_width_widgets = max(len(widgets_for_record), col_width_widgets)

                for widget in widgets_for_record:
                    logger.info(
                        f"Adding {widget.__class__.__name__} widget for {record.name}"
                    )
                    logger.debug(f"Position: ({current_x_pos}, {current_y_pos})")
                    screen.add_widget(widget)

                records_seen.append(record.name)
                if readback_record:
                    records_seen.append(readback_record.name)

                current_x_pos, current_y_pos = get_next_widget_position(
                    current_x_pos, current_y_pos, col_width_widgets, config
                )
                if current_y_pos == start_y_pos:
                    dividing_line = add_dividing_line(
                        current_x_pos - config.widget_offset, current_y_pos, config
                    )
                    screen.add_widget(dividing_line)
                    col_width_widgets = 2

    screen_width = get_next_x_position(current_x_pos, col_width_widgets, config)

    if current_x_pos != start_x_pos:
        screen_height = config.max_screen_height + config.widget_offset
    else:
        screen_height = current_y_pos + config.widget_offset

    title_bar = add_title_bar(name, config, screen_width - config.widget_offset)
    if title_bar:
        screen.add_widget(title_bar)

    if config.title_bar_format == TitleBarFormat.MINIMAL and border is not None:
        border.width(screen_width)
        border.height(
            screen_height - int(config.title_bar_heights[config.title_bar_format] / 2)
        )

    screen.background_color(*config.background_color)

    screen.height(screen_height)
    screen.width(screen_width)

    if config.macro_set_level == MacroSetLevel.SCREEN:
        for macro in macros.items():
            screen.macro(macro[0], macro[1])

    logger.info(f"Generated screen for database: {name}")

    return screen


def get_height_width_of_bobfile(bobfile_path: str | Path) -> tuple[int, int]:
    with open(bobfile_path) as bobfile:
        xml = ET.parse(bobfile)

        height = int(xml.getroot().find("height").text)  # type: ignore
        width = int(xml.getroot().find("width").text)  # type: ignore
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
                embed_raw_height, embed_raw_width = get_height_width_of_bobfile(
                    found_bobfiles[template_to_bob(template)]
                )
                embed_height = embed_raw_height + config.widget_offset
                embed_width = embed_raw_width + config.widget_offset
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

    title_bar = add_title_bar(
        substitution_name,
        config,
        screen_width - config.widget_offset,
    )
    if title_bar:
        screen.add_widget(title_bar)

    screen.height(screen_height)
    screen.width(screen_width)

    logger.info(f"Generated screen for substitution: {substitution}")

    return screen
