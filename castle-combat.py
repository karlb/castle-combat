#!/usr/bin/env python
import sys

sys.path.append("src")

print(
    "Castle-Combat requires pygame and twisted. If the game doesn't start up correctly, please verify that these are installed in the versions given in requirements.txt."
)

import main

main.main()
