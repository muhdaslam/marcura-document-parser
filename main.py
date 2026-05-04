#!/usr/bin/env python3
"""Shim: run ``python main.py`` from the project root (same as ``python -m charter_parser``)."""

import sys

from charter_parser.cli import main

if __name__ == "__main__":
    sys.exit(main())
