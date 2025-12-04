#!/bin/bash

# Exit on error
set -e

echo "Extracting messages..."
uv run pybabel extract -F babel.cfg -k _l -o messages.pot .

echo "Updating translations..."
uv run pybabel update -i messages.pot -d translations

echo "Compiling translations..."
uv run pybabel compile -d translations

echo "Done!"
