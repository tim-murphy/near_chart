# Run statistical analysis on the chart measurements, including generation of
# charts and other documents.
# Written by Tim Murphy <tim.murphy@canberra.edu.au> 2025

import argparse
import csv
import glob
import os
from statistics import mean
import sys

X_HEIGHT="x-height"
CAP_HEIGHT="cap height"

def px_to_mm(px, dpi=600):
    return 25.4/600*px

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurements_dir", type=str, default="measurements",
                        help="Directory containing measurement CSV files.")
    args = parser.parse_args()

    # Check command-line arguments.
    csv_dir = os.path.join(os.path.dirname(sys.argv[0]), args.measurements_dir)
    if not os.path.isdir(csv_dir):
        raise ValueError("Measurements directory does not exist: " + csv_dir)

    # Data is stored in the following format:
    # height_px[chart] -> {size[x-height|cap_height] -> [height_px]}
    height_px = {}

    # Extract the data.
    for csvfile in glob.glob(os.path.join(csv_dir, "*.csv")):
        print("Processing ", os.path.split(csvfile)[1], "...", end="",
              flush=True, sep="")

        with open(csvfile, 'r') as ifile:
            next(ifile)
            rows = csv.DictReader(ifile)
            for row in rows:
                # Ignore empty lines.
                if row["Chart"] == "":
                    continue

                # If the comment starts with EXCLUDE, ignore the line.
                if row["Comments"].startswith("EXCLUDE"):
                    continue

                # For code readability.
                chart = row["Chart"]
                size = row["Size"]
                measure_type = X_HEIGHT if row["Letter"].islower() \
                                        else CAP_HEIGHT
                measure = int(row["Height (px)"])

                if not chart in height_px:
                    height_px[chart] = {}

                if not size in height_px[chart]:
                    height_px[chart][size] = {}

                if not measure_type in height_px[chart][size]:
                    height_px[chart][size][measure_type] = []

                height_px[chart][size][measure_type].append(measure)

        print("done")

    # Run stats on the data.
    for chart, sizes in height_px.items():
        print()
        print("===", chart, "===")
        for size, measure_types in sizes.items():
            print("Line", size)

            means = {}
            for measure_type, heights in measure_types.items():
                mean_px = mean(heights)
                mean_mm = px_to_mm(mean_px)
                means[measure_type] = mean_mm
                print(" ", measure_type, "mean:", mean_mm, "mm")

            if X_HEIGHT in means and CAP_HEIGHT in means:
                print(" ", X_HEIGHT, CAP_HEIGHT, "ratio:",
                      means[X_HEIGHT] / means[CAP_HEIGHT])
# EOF
