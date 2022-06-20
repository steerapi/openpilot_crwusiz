#!/usr/bin/env sh
set -e
cd /data/openpilot/panda/board;

scons -u -j$(nproc)
PYTHONPATH=.. python3 -c "from python import Panda; Panda().flash('obj/panda.bin.signed')"

sleep 10

cd /data/openpilot
./selfdrive/boardd/pandad.py
