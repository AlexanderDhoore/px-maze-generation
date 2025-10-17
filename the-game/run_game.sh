#!/bin/bash

cd ~/px-maze-generation/the-game/

source ../venv/bin/activate

# taskset forces the use of the 4 biggest CPU cores (on rock5b)
taskset -c 4-7 python run_game.py
