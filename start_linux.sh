#!/bin/sh
cd "$(dirname "$0")"
pip install -q -r requirements.txt
python3 solbot.py
