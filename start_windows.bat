@echo off
cd /d "%~dp0"
title SolBot CMD - Uji 5 Mode
python -m pip install -q -r requirements.txt
python solbot.py
pause
