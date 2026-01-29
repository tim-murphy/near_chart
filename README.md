# Reading chart study

This repository contains code used for chart measurement and statistics for the study (unpublished):

Murphy, TI, Chen, J, Leung, M, **How accurate are our near reading charts? An assessment of 19 charts against ISO standards.** (2026).

This study compared reading charts commonly used in community optometry to the new ISO 7921:2024 standard. A new, standards-compliant chart was created as part of this study, which is available under the Releases tab to the right.

## Environment setup

This software uses Python 3.11 or greater, and has been tested on Windows and Linux (Debian).
To setup the environment, run:

`pip install -r requirements.txt`

## Results reproduction

All data required to reproduce the results are included in this repository.
To produce the statistics for all charts, run:

`python stats.py --exclude_new`

To produce statistics for a subset of charts, run the script with the `--help` flag to view the options.
