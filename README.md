# Reading chart study

This repository contains code used for chart measurement and statistics for the study:

`Murphy, T.I., Chen, J. & Leung, M. How Accurate are Our Near Reading Charts? An Assessment of 19 Charts Against ISO Standards. Ophthalmic Physiol. Opt. (2026). https://doi.org/10.1007/s44402-026-00123-2`

This study compared reading charts commonly used in community optometry to the new ISO 7921:2024 standard. A new, standards-compliant chart was created as part of this study, which is available under the Releases tab to the right. Please cite the above paper if you use the chart for research purposes.

## Environment setup

This software uses Python 3.11 or greater, and has been tested on Windows and Linux (Debian).
To setup the environment, run:

`pip install -r requirements.txt`

## Results reproduction

All data required to reproduce the results are included in this repository.
To produce the statistics for all charts, run:

`python stats.py --exclude_new`

To produce statistics for a subset of charts, run the script with the `--help` flag to view the options.
