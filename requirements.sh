#!/bin/bash -e

# This is only tested on Ubuntu 19.04
# This scrip will fail if any command fails to
# reduce the chance that half completed steps will contaminate the system.

# System:
sudo apt-get install \
    python3-pip \
    build-essential \
    git \
    python3 \
    python3-dev \
    ffmpeg \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libportmidi-dev \
    libswscale-dev \
    libavformat-dev \
    libavcodec-dev \
    zlib1g-dev


# pip required packages:
rm -rf csgo-translator.venv
python3 -m venv csgo-translator.venv
source csgo-translator.venv/bin/activate
pip install --upgrade pip
pip install wheel
pip install googletrans
pip install Cython==0.29.9
pip install kivy==1.10.1

# pip optional packages:
pip install pyinstaller
pip install pylint