#!/bin/bash
# Double-click to start Lionel Types.
# The first run sets things up, which needs Python 3 and an internet connection.
cd "$(dirname "$0")" || exit 1

if [ ! -x .venv/bin/python ]; then
    echo "Setting up Lionel Types for the first time..."
    if ! python3 -m venv .venv; then
        echo "Lionel Types needs Python 3. Get it from https://www.python.org/downloads/"
        read -r -p "Press Return to close."
        exit 1
    fi
fi

if ! cmp -s requirements.txt .venv/installed-requirements.txt; then
    if ! .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt; then
        echo "Could not install what Lionel Types needs. Check the internet connection and try again."
        read -r -p "Press Return to close."
        exit 1
    fi
    cp requirements.txt .venv/installed-requirements.txt
fi

exec .venv/bin/python -m lionel_types "$@"
