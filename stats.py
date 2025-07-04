# Run statistical analysis on the chart measurements, including generation of
# charts and other documents.
# Written by Tim Murphy <tim.murphy@canberra.edu.au> 2025

import argparse
import csv
import glob
from math import atan, degrees, log10
import os
from statistics import mean
import sys

X_HEIGHT="x-height"
CAP_HEIGHT="cap height"
UNIT_LABELS="labels"

N_SIZE = "N size"
PT = "Point"
M_SIZE = "M size"
DECIMAL_40 = "Decimal @ 40cm"
LOGMAR_40 = "logMAR @ 40cm"

UNITS = (
    N_SIZE,
    PT,
    M_SIZE,
    DECIMAL_40,
    LOGMAR_40
)

N_TO_LOGRAD = {
    60: 1.3,
    48: 1.2,
    36: 1.1,
    30: 1.0,
    24: 0.9,
    18: 0.8,
    14: 0.7,
    12: 0.6,
    10: 0.5,
    8: 0.4,
    7: log10(0.9/0.4), # Estimate for Howell
    6: 0.3,
    5: 0.2,
    4: 0.1,
    3: 0.0,
    2: -0.1,
    1.8: -0.2,
    1.5: -0.3
}

def px_to_mm(px, dpi=600):
    return 25.4/600*px

def lograd_to_mm(lograd, distance_mm=400):
    return 0.582 * pow(10, lograd)

def mm_to_lograd(mm, distance_mm=400, round_to=0.1):
    rad = 60 * degrees(atan(mm / (5 * distance_mm)))
    return round(log10(rad) / round_to, 0) * round_to

def size_to_lograd(unit, size, mm, round_to=0.02):
    lograd = None
    if unit == N_SIZE or unit == PT:
        # Since N size is not standard, use the table from the ISO standard
        # in the first instance.
        if size in N_TO_LOGRAD:
            lograd = N_TO_LOGRAD[size]

        # Otherwise, if there is a value in the table that is 1/(2^n) in the
        # table then convert from that.
        elif size % 2 == 0:
            for n in range(1, int(size/2)):
                new_n = size/pow(2, n)
                if new_n in N_TO_LOGRAD:
                    lograd = N_TO_LOGRAD[new_n] + (0.3 * n)
                    break

            if lograd is None:
                print("ERROR: could not covert N", size, "to logRAD",
                      file=sys.stderr)
                return None

        # Otherwise, calculate the closest logRAD.
        else:
            lograd = mm_to_lograd(mm, round_to=0.02)

    elif unit == M_SIZE:
        lograd = log10(size/0.4)

    elif unit == DECIMAL_40:
        lograd = log10(1/size)

    elif unit == LOGMAR_40:
        lograd = size

    # Round to the nearest value.
    return round(lograd / round_to, 0) * round_to

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurements_dir", type=str, default="measurements",
                        help="Directory containing measurement CSV files.")
    parser.add_argument("--process_cap_height", action="store_true",
                        help="Process cap height stats as well")
    args = parser.parse_args()

    # Check command-line arguments.
    csv_dir = os.path.join(os.path.dirname(sys.argv[0]), args.measurements_dir)
    if not os.path.isdir(csv_dir):
        raise ValueError("Measurements directory does not exist: " + csv_dir)

    # Data is stored in the following format:
    # height_px[chart] -> {lograd[x-height|cap_height] -> [height_px]}
    #                            [labels] -> [unit + size]
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
                if row["Height (px)"] == "":
                    continue

                # If the comment starts with EXCLUDE, ignore the line.
                if row["Comments"].startswith("EXCLUDE"):
                    continue

                # For code readability.
                chart = row["Chart"]
                unit = row["Unit"]
                size = float(row["Size"])
                measure_type = X_HEIGHT if row["Letter"].islower() \
                                        else CAP_HEIGHT
                measure = int(row["Height (px)"])

                # Don't process cap heights unless specified.
                if not args.process_cap_height and measure_type == CAP_HEIGHT:
                    continue

                # Make sure the unit is valid.
                if not unit in UNITS:
                    print("ERROR: invalid unit", unit, file=sys.stderr)
                    continue

                lograd = size_to_lograd(unit, size, px_to_mm(measure))

                if not chart in height_px:
                    height_px[chart] = {}

                if not lograd in height_px[chart]:
                    height_px[chart][lograd] = {UNIT_LABELS: []}

                if not measure_type in height_px[chart][lograd]:
                    height_px[chart][lograd][measure_type] = []

                height_px[chart][lograd][measure_type].append(measure)

                label = str(size) + " " + unit
                if not label in height_px[chart][lograd][UNIT_LABELS]:
                    height_px[chart][lograd][UNIT_LABELS].append(label)

        print("done")

    # Run stats on the data.
    for chart, sizes in height_px.items():
        print()
        print("===", chart, "===")
        for lograd, measure_types in sizes.items():
            print("logRAD", round(lograd, 2))

            means = {}
            for measure_type, heights in measure_types.items():
                if measure_type == UNIT_LABELS:
                    print("  Labels:", ",".join(heights))
                    continue

                mean_px = mean(heights)
                mean_mm = px_to_mm(mean_px)
                means[measure_type] = mean_mm
                print("  ", measure_type, " mean: ", round(mean_mm, 3), "mm",
                      sep="")

                if measure_type == X_HEIGHT:
                    expected_mm = lograd_to_mm(lograd)
                    err = (mean_mm / expected_mm) - 1
                    tolerance = 0.05 if lograd > -0.2 else 0.1

                    marker = "" if abs(err) <= tolerance \
                             else "<<<<======= OUT OF TOLERANCE!"

                    print("    expected: ", round(expected_mm, 3), "mm",
                          sep="")
                    print("    error: ", round(err * 100, 2), "% ", marker,
                          sep="")

            if X_HEIGHT in means and CAP_HEIGHT in means:
                print(" ", X_HEIGHT, CAP_HEIGHT, "ratio:",
                      means[X_HEIGHT] / means[CAP_HEIGHT])
# EOF
