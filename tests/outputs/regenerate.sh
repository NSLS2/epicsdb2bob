#!/bin/bash
# Regenerate expected test output .bob files
# Run from the repository root: bash tests/outputs/regenerate.sh

set -e

cd "$(git rev-parse --show-toplevel)"

uv run python -c "
from pathlib import Path
from epicsdb2bob.bobfile_gen import generate_bobfile_for_db, generate_bobfile_for_substitution
from epicsdb2bob.config import EPICSDB2BOBConfig, EmbedLevel
from epicsdb2bob.utils import find_bobfiles_in_search_path, find_epics_dbs_and_templates, find_epics_subs
import os

config = EPICSDB2BOBConfig()
config.embed = EmbedLevel.ALL
input_file_path = Path('tests') / 'inputs'

written_bobfiles = find_bobfiles_in_search_path(config.bobfile_search_path)

databases = find_epics_dbs_and_templates(input_file_path, {})
for name in databases:
    screen = generate_bobfile_for_db(name, databases[name], {}, config)
    full_output_path = f'tests/outputs/{name}.bob'
    screen.write_screen(full_output_path)
    written_bobfiles[os.path.basename(full_output_path)] = Path(full_output_path)
    print(f'Wrote {full_output_path}')

name, substitution = list(find_epics_subs(input_file_path).items())[0]
screen = generate_bobfile_for_substitution(name, substitution, written_bobfiles, config)
screen.write_screen(f'tests/outputs/{name}.bob')
print(f'Wrote tests/outputs/{name}.bob')
"
