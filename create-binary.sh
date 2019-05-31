#!/bin/bash -e

source ./csgo-translator.venv/bin/activate
mkdir pyinstall
cd pyinstall
pyinstaller ../csgo-translator.py --onefile
mv dist/csgo-translator ../csgo-translator_linux64
cd ..
rm -rf pyinstall
rm -rf __pycache__