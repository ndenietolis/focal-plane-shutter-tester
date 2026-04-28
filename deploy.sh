#!/usr/bin/env bash
set -euo pipefail

mpremote connect auto fs cp -f vibe-shutter.py :main.py
mpremote connect auto fs cp -f ssd1306.py :ssd1306.py
mpremote connect auto reset
