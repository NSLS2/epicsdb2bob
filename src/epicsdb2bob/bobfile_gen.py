from typing import Any
import phoebusgen
import phoebusgen.screen
from phoebusgen.widget import TextUpdate, TextEntry, ActionButton, LED, Label

from dbtoolspy import Database, Record

import logging

logger = logging.getLogger("epicsdb2bob")

MAX_HEIGHT = 800
OFFSET = 10

DEFAULT_WIDGET_WIDTH = 50
DEFAULT_WIDGET_HEIGHT = 15

# RECORD_TYPES_TO_FUNCS = {
#     "bo":
#     "bi": add_led_widget,
#     "ao": add_text_entry_widget,
#     "ai": add_text_update_widget,
#     "stringout": add_text_entry_widget,
#     "stringin": add_text_update_widget,
# }


def add_label_for_record(record: Record, start_x: int, start_y: int) -> Label:
    description = record.fields.get("DESC", record.name.rsplit(")")[-1])  #  type: ignore
    return Label(
        f"{record.name}_label",
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
            f"{record.name}_text_update",
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
    current_y_pos = OFFSET

    records_seen = []

    for record in database.values():
        print(record.rtyp)
        print(record.name)

    return screen
