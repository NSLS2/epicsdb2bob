import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree as ET

from epicsdbtools import Database, Record
from phoebusgen.v4 import Screen
from phoebusgen.v4.widgets import (
    ActionButton,
    EmbeddedDisplay,
    Group,
    Label,
    Rectangle,
    TextUpdate,
    Widget,
)
from phoebusgen.v4.properties.display import (
    HasBackgroundColor,
    HasFont,
    HasForegroundColor,
    HasHorizontalAlignment,
)
from phoebusgen.v4.properties import (
    Color,
    GroupStyle,
    HorizontalAlignment,
    OpenDisplayAction,
    VerticalAlignment,
)
from phoebusgen.v4.properties.types import OpenDisplayTarget

from .config import (
    EmbedLevel,
    EPICSDB2BOBConfig,
    MacroSetLevel,
    TitleBarFormat,
)
from .palettes import BLACK, WHITE
from .utils import pack_close_to_square

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
        str(description),
        start_x,
        start_y,
        config.default_widget_width,
        config.default_widget_height,
    )

    label.foreground_color = Color(config.palette.get_widget_fg(Label))
    label.background_color = Color(config.palette.get_widget_bg(Label))
    label.font.size = config.font_size
    label.horizontal_alignment = HorizontalAlignment(config.label_alignment)

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
    widget_type = config.rtype_to_widget_map[str(record.rtype)]

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
        widget.foreground_color = Color(config.palette.get_widget_fg(widget_type))

    if isinstance(widget, HasBackgroundColor):
        widget.background_color = Color(config.palette.get_widget_bg(widget_type))

    if isinstance(widget, HasFont):
        widget.font.size = config.font_size

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
    name: str,
    config: EPICSDB2BOBConfig,
    title_bar_width: int,
    top_level_titlebar: bool = False,
) -> Label | None:
    title_bar_format = (
        config.title_bar_format if not top_level_titlebar else TitleBarFormat.FULL
    )

    if title_bar_format == TitleBarFormat.NONE:
        return None

    title_bar = Label(
        "TitleBar",
        name,
        config.widget_offset if title_bar_format == TitleBarFormat.MINIMAL else 0,
        0,
        title_bar_width,
        config.title_bar_heights[title_bar_format],
    )
    title_bar.foreground_color = Color(WHITE)
    if title_bar_format == TitleBarFormat.FULL:
        title_bar.font.size = config.font_size * 2
        title_bar.horizontal_alignment = HorizontalAlignment.CENTER
    elif title_bar_format == TitleBarFormat.MINIMAL:
        title_bar.auto_size = True
        title_bar.font.size = config.font_size + 2
        title_bar.border_width = 2
        title_bar.border_color = Color(BLACK)

    title_bar.background_color = Color(config.palette.title_bar_bg)
    title_bar.foreground_color = Color(config.palette.title_bar_fg)
    title_bar.transparent = False
    title_bar.vertical_alignment = VerticalAlignment.MIDDLE
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
    border.transparent = True
    border.line_width = 2
    border.line_color = Color(BLACK)

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
    dividing_line.line_color = Color(BLACK)
    return dividing_line


def _next_widget_position_in_group(
    current_x: int,
    current_y: int,
    start_y: int,
    col_width_widgets: int,
    config: EPICSDB2BOBConfig,
) -> tuple[int, int]:
    """Compute next widget position within a group (no title bar offset)."""
    new_x = current_x
    new_y = current_y + config.default_widget_height + config.widget_offset

    if new_y > config.max_screen_height:
        new_y = start_y
        new_x = get_next_x_position(current_x, col_width_widgets, config)

    return new_x, new_y


def generate_bobfile_for_db(
    name: str,
    database: Database,
    macros: dict[str, str],
    config: EPICSDB2BOBConfig,
    found_bobfiles: dict[str, Path] | None = None,
) -> Screen:
    screen = Screen(name)

    start_x_pos = config.widget_offset
    start_y_pos = config.widget_offset

    current_x_pos = start_x_pos
    current_y_pos = start_y_pos

    widget_counters: dict[type[Widget], int] = {}
    col_width_widgets = 2

    group_widgets: list[Widget] = []

    records_seen = []

    for record in database.values():
        logger.info(f"Processing record: {record.name} of type {record.rtype}")
        if record.rtype not in config.rtype_to_widget_map:
            logger.warning(f"Record type {record.rtype} not supported, skipping.")
        else:
            if record.name in records_seen:
                logger.info(f"Record {record.name} already processed, skipping.")
            else:
                readback_record = None
                if record.name + config.readback_suffix in database:
                    rb = database[record.name + config.readback_suffix]
                    if rb.rtype in config.rtype_to_widget_map:
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
                    widget_counters[type(widget)] = (
                        widget_counters.get(type(widget), 0) + 1
                    )
                    widget.name = (
                        f"{type(widget).__name__}_{widget_counters[type(widget)]}"
                    )
                    logger.info(
                        f"Adding {widget.__class__.__name__} widget for {record.name}"
                    )
                    logger.debug(f"Position: ({current_x_pos}, {current_y_pos})")
                    group_widgets.append(widget)

                records_seen.append(record.name)
                if readback_record:
                    records_seen.append(readback_record.name)

                current_x_pos, current_y_pos = _next_widget_position_in_group(
                    current_x_pos,
                    current_y_pos,
                    start_y_pos,
                    col_width_widgets,
                    config,
                )
                if current_y_pos == start_y_pos:
                    widget_counters[Rectangle] = widget_counters.get(Rectangle, 0) + 1
                    dividing_line = add_dividing_line(
                        current_x_pos - config.widget_offset, start_y_pos, config
                    )
                    dividing_line.name = f"Rectangle_{widget_counters[Rectangle]}"
                    group_widgets.append(dividing_line)
                    col_width_widgets = 2

    # Group box style adds a 10px bounding box inside its edges
    # Width = 20 (group box sides) + widget_offset * (num_cols + 1) + num_cols * widget_width
    content_width = col_width_widgets * config.default_widget_width + (col_width_widgets + 1) * config.widget_offset
    if current_x_pos != start_x_pos:
        num_screen_cols = (current_x_pos - start_x_pos) // (col_width_widgets * (config.default_widget_width + config.widget_offset)) + 1
        content_width = num_screen_cols * (col_width_widgets * config.default_widget_width + (col_width_widgets + 1) * config.widget_offset)
    group_width = 30 + content_width

    if current_x_pos != start_x_pos:
        group_height = config.max_screen_height + 3 * config.widget_offset
    else:
        group_height = current_y_pos + 3 * config.widget_offset

    # Wrap all record widgets in a Group with group box style
    group = Group(
        name.replace("_", " ").replace("-", " "),
        0,
        0,
        group_width,
        group_height,
    )
    group.style = GroupStyle.GROUP_BOX
    group.transparent = True
    group.foreground_color = Color(config.palette.get_widget_fg(Group))
    group.background_color = Color(config.palette.get_widget_bg(Group))
    group.line_color = Color(config.palette.border_color)
    group.font.size = config.font_size

    for w in group_widgets:
        group.add_widget(w)

    screen.add_widget(group)

    screen_width = group_width
    screen_height = group_height

    # Embed bobfiles for included templates if available
    included_templates = database.get_included_templates()
    if found_bobfiles and included_templates and config.embed != EmbedLevel.NONE:
        embed_y_offset = screen_height
        for include_name in included_templates:
            include_bob = template_to_bob(include_name)
            if include_bob in found_bobfiles:
                logger.info(f"Embedding included template bobfile: {include_bob}")
                embed_raw_height, embed_raw_width = get_height_width_of_bobfile(
                    found_bobfiles[include_bob]
                )
                embed_height = embed_raw_height + config.widget_offset
                embed_width = embed_raw_width + config.widget_offset

                embedded_display = EmbeddedDisplay(
                    short_uuid(),
                    include_bob,
                    config.widget_offset,
                    embed_y_offset,
                    embed_width,
                    embed_height,
                )
                widget_counters[EmbeddedDisplay] = (
                    widget_counters.get(EmbeddedDisplay, 0) + 1
                )
                embedded_display.name = (
                    f"EmbeddedDisplay_{widget_counters[EmbeddedDisplay]}"
                )
                screen.add_widget(embedded_display)

                screen_width = max(
                    screen_width, embed_width + 2 * config.widget_offset
                )
                embed_y_offset += embed_height + config.widget_offset

        screen_height = embed_y_offset + config.widget_offset

    screen.background_color = Color(config.palette.screen_bg)

    screen.height = screen_height
    screen.width = screen_width

    if config.macro_set_level == MacroSetLevel.SCREEN:
        screen.macros.update(macros)

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
    substitution_name.replace("_", " ").replace("-", " ").title()
    screen = Screen(substitution_name)
    screen.background_color = Color(config.background_color)

    launcher_buttons: dict[str, ActionButton] = {}

    logger.info(f"Generating screen for substitution: {substitution_name}")
    logger.debug(f"Found bobfiles: {found_bobfiles}")

    embed_rects: list[tuple[Widget, tuple[int, int]]] = []

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

                embedded_display = EmbeddedDisplay(
                    short_uuid(),
                    template_to_bob(template),
                    0,
                    0,
                    embed_width,
                    embed_height,
                )

                embed_rects.append((embedded_display, (embed_width, embed_height)))

                embedded_display.macros = instance

            elif template in launcher_buttons:
                launcher_buttons[template].actions.append(
                    OpenDisplayAction(
                        description=f"{os.path.splitext(template)[0]} {i + 1}",
                        file=Path(template_to_bob(template)),
                        target=OpenDisplayTarget.NEW_TAB,
                        macros=instance,
                    )
                )
            else:
                logger.info(f"Creating launcher button for template: {template}")

                launcher_buttons[template] = ActionButton(
                    short_uuid(),
                    os.path.splitext(template)[0],
                    "",
                    0,
                    0,
                    config.default_widget_width,
                    config.default_widget_height,
                )

                launcher_buttons[template].actions.append(
                    OpenDisplayAction(
                        description=f"{os.path.splitext(template)[0]} {i + 1}",
                        file=Path(template_to_bob(template)),
                        target=OpenDisplayTarget.NEW_TAB,
                        macros=instance,
                    )
                )
                embed_rects.append((launcher_buttons[template], (
                    config.default_widget_width + config.widget_offset,
                    config.default_widget_height + config.widget_offset,
                )))

    packed_x_y_embeds = pack_close_to_square(
        [size for _, size in embed_rects],
        config.max_screen_height,
        padding=config.widget_offset,
    )

    embed_stop_positions = [
        (pos[0] + size[0], pos[1] + size[1])
        for pos, (_, size) in zip(packed_x_y_embeds, embed_rects, strict=False)
    ]
    screen_width = max([pos[0] for pos in embed_stop_positions], default=0)
    screen_height = max([pos[1] for pos in embed_stop_positions], default=0)
    screen_height = screen_height + 5 * config.widget_offset

    for i, (xy_position, (embed, _)) in enumerate(
        zip(packed_x_y_embeds, embed_rects, strict=False)
    ):
        embed.x = xy_position[0]
        embed.y = (
            xy_position[1]
            + config.title_bar_heights[config.title_bar_format]
            + 3 * config.widget_offset
        )
        embed.name = f"{embed.__class__.__name__}_{i + 1}"
        screen.add_widget(embed)

    title_bar = add_title_bar(
        substitution_name,
        config,
        screen_width - config.widget_offset,
        top_level_titlebar=True,
    )
    if title_bar:
        screen.add_widget(title_bar)

    screen.height = screen_height
    screen.width = screen_width

    logger.info(f"Generated screen for substitution: {substitution}")

    return screen
