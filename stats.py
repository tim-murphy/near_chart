#!/usr/bin/env python
# Run statistical analysis on the chart measurements, including generation of
# charts and other documents.
# Written by Tim Murphy <tim.murphy@canberra.edu.au> 2025

import argparse
import csv
import glob
from math import atan, ceil, degrees, log10
import matplotlib.pyplot as plt
import numpy as np
import os
import pingouin as pg
import pandas as pd
from scipy.stats import linregress
from statistics import mean, median
import sys

X_HEIGHT="x-height"
CAP_HEIGHT="cap height"
UNIT_LABELS="labels"
BOTTOM_X_VALUE="bottom x value"
BOTTOM_Y_VALUE="bottom y value"

N_SIZE = "N size"
PT = "Point"
M_SIZE = "M size"
DECIMAL_40 = "Decimal @ 40cm"
LOGMAR_40 = "logMAR @ 40cm"

SCATTER_LABEL = "Chart"
SCATTER_X = "Size (logRAD)"
SCATTER_Y = "Size error (decimal)"
ERROR = "Measurement error"

MEASUREMENT_ERROR = 25.4 / 600.0

UNITS = (
    N_SIZE,
    PT,
    M_SIZE,
    DECIMAL_40,
    LOGMAR_40
)

NEW_CHARTS = [19, 20]

# True if serif, false if sans serif.
SERIF_CHART = {
    1:      False,
    2:      True,
    3:      True,
    4:      False,
    5:      True,
    6:      True,
    7:    True,
    8.1:    False,
    8.2:    False,
    9:    True,
    10:   True,
    11:     False,
    12:   True,
    13:   True,
    14:     True,
    15:   True,
    16:     False,
    17:     False,
    18:     True,
    19:     True,
    20:     False
}

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
    # 9: log10(1.15/0.4), # Estimate for Howell
    8: 0.4,
    # 7: log10(0.9/0.4), # Estimate for Howell
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

        # Special case for charts 8.1 and 8.2.
        elif size == 26:
            lograd = 1.0

        # Special case for chart 15.
        elif size == 7:
            lograd = 0.3

        # Special case for chart 11.
        elif size == 15:
            lograd = 0.7

        # Special case for chart 11.
        elif size == 40:
            lograd = 1.1

        # Otherwise, if there is a value in the table that is 1/(2^n) in the
        # table then convert from that.
        elif size % 2 == 0:
            for n in range(1, int(size/2)):
                new_n = size/pow(2, n)
                if new_n in N_TO_LOGRAD:
                    lograd = N_TO_LOGRAD[new_n] + (0.3 * n)
                    break

            if lograd is None:
                print("ERROR: could not convert N", size, "to logRAD",
                      file=sys.stderr)
                lograd = mm_to_lograd(mm, round_to=0.02)

        # Otherwise, calculate the closest logRAD.
        else:
            lograd = mm_to_lograd(mm, round_to=0.02)

    elif unit == M_SIZE:
        # Use 0.63 if the chart has rounded to 0.6.
        if size == 0.6:
            lograd = log10(0.63/0.4)
        else:
            lograd = log10(size/0.4)

    elif unit == DECIMAL_40:
        # 0.32 is allowed to be written as 0.3, and
        # 0.63 is allowed to be written as 0.6.
        if size == 0.3:
            lograd = log10(1/0.32)
        elif size == 0.6:
            lograd = log10(1/0.63)
        else:
            lograd = log10(1/size)

    elif unit == LOGMAR_40:
        lograd = size

    # Round to the nearest value.
    return round(lograd / round_to, 0) * round_to

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurements_dir", type=str, default="measurements",
                        help="Directory containing measurement CSV files.")
    parser.add_argument("--no_process_cap_height", action="store_true",
                        help="Process cap height stats as well.")
    parser.add_argument("--lograd_xheight_csv", required=False, type=str,
                        help="Output a CSV file with logRAD and x-height data.")
    parser.add_argument("--letters", nargs="+", type=chr,
                        default=['w', 'z', 'x', 'v', 'W', 'E', 'T', 'Y', 'I', 'A', 'F', 'H', 'K', 'L', 'Z', 'X', 'V', 'N', 'M'],
                        help="Valid letters for measurements")
    parser.add_argument("--chart_ids", nargs="+", type=float, required=False,
                        help="Only include these chart IDs")
    parser.add_argument("--font_type", type=str, default="all",
                        choices=["serif", "sans-serif", "all"],
                        help="Restrict output to these font types only")
    parser.add_argument("--exclude_new", action="store_true",
                        help="Exclude the newly created charts")
    parser.add_argument("--chart_title", type=str, default="X-height Measurements",
                        help="Title for the x-height measurement plot")
    parser.add_argument("--max_height_diff", default=0.2, type=float,
                        help="The maximum allowable difference in measurements,"\
                             + " as a fraction. (default: 0.2)")
    args = parser.parse_args()

    # Check command-line arguments.
    csv_dir = os.path.join(os.path.dirname(sys.argv[0]), args.measurements_dir)
    if not os.path.isdir(csv_dir):
        raise ValueError("Measurements directory does not exist: " + csv_dir)

    lograd_xheight_csv = args.lograd_xheight_csv
    if not lograd_xheight_csv is None:
        lograd_dir = os.path.dirname(os.path.abspath(lograd_xheight_csv))
        if not os.path.isdir(lograd_dir):
            os.makedirs(lograd_dir)

    # Data is stored in the following format:
    # height_px[chart] -> {lograd[x-height|cap_height] -> [height_px]}
    #                            [labels] -> [unit + size]
    height_px = {}

    # These data will be used to calculate ICC3
    # Format: file -> {chart -> {size -> [x-height]}}
    icc_data = {}
    all_charts = set()

    # Extract the data.
    for csvfile in glob.glob(os.path.join(csv_dir, "*.csv")):
        print("Processing ", os.path.split(csvfile)[1], "...", end="",
              flush=True, sep="")

        with open(csvfile, 'r') as ifile:
            next(ifile)
            rows = csv.DictReader(ifile)

            if not csvfile in icc_data:
                icc_data[csvfile] = {}

            for row in rows:
                # Ignore empty lines.
                if row["Height (px)"] == "":
                    continue

                # If the comment starts with EXCLUDE, ignore the line.
                if row["Comments"].startswith("EXCLUDE"):
                    continue

                # Threshold charts only.
                if "Chart type" in row and row["Chart type"] not in ("Threshold", ""):
                    continue

                # Valid letters only.
                if row["Letter"] not in args.letters:
                    print("WARN: ignoring invalid letter:", row["Letter"], file=sys.stderr)
                    print("WARN:    ", csvfile, row, file=sys.stderr)
                    continue

                # For code readability.
                chart = row["Chart"]
                chart_id = float(chart.split(" :: ")[0])
                unit = row["Unit"]
                size = float(row["Size"])
                measure_type = X_HEIGHT if row["Letter"].islower() \
                                        else CAP_HEIGHT
                measure = int(row["Height (px)"])

                if not chart_id in icc_data[csvfile]:
                    icc_data[csvfile][chart_id] = {}

                all_charts.add(chart_id)

                # Keep track of the lowest Y coord regardless of measure_type.
                # From this we can estimate the line spacing.
                # Because there are two 'X' and 'Y' rows, the bottom values
                # overwrite the top values so we can just use 'X' and 'Y'.
                bottom_x = int(row["X"])
                bottom_y = int(row["Y"])

                # Don't process cap heights unless specified.
                if args.no_process_cap_height and measure_type == CAP_HEIGHT:
                    continue

                # Make sure the unit is valid.
                if not unit in UNITS:
                    print("ERROR: invalid unit", unit, file=sys.stderr)
                    continue

                lograd = size_to_lograd(unit, size, px_to_mm(measure))

                if round(10 * lograd, 3) % 1 != 0:
                    raise ValueError("Bad logRAD conversion for " + csvfile\
                                     + " " + chart + "! " + unit + " "\
                                     + str(size) + " = " + str(lograd))

                lograd = round(lograd, 1)

                if not lograd in icc_data[csvfile][chart_id]:
                    icc_data[csvfile][chart_id][lograd] = []
                icc_data[csvfile][chart_id][lograd].append(measure)

                if not chart in height_px:
                    height_px[chart] = {}

                if not lograd in height_px[chart]:
                    height_px[chart][lograd] = {UNIT_LABELS: [],
                                                BOTTOM_X_VALUE: [],
                                                BOTTOM_Y_VALUE: []}

                height_px[chart][lograd][BOTTOM_X_VALUE].append(bottom_x)
                height_px[chart][lograd][BOTTOM_Y_VALUE].append(bottom_y)

                if not measure_type in height_px[chart][lograd]:
                    height_px[chart][lograd][measure_type] = []

                height_px[chart][lograd][measure_type].append(measure)

                label = str(size) + " " + unit
                if not label in height_px[chart][lograd][UNIT_LABELS]:
                    height_px[chart][lograd][UNIT_LABELS].append(label)

            print("done")

    # Calculate Krippendorff's Alpha for all measurements.
    # For this we need a matrix with graders as rows and measurements as cols.
    icc_data_matrix = {}

    for g in icc_data.keys():
        icc_data_matrix[g] = []

    icc_data_good = True
    for chart_id in all_charts:
        if chart_id in NEW_CHARTS:
            continue

        # Sanity check.
        grader_one = None
        for g in icc_data.keys():
            if grader_one is None:
                grader_one = g
                continue

            if sorted(icc_data[grader_one][chart_id].keys()) !=\
               sorted(icc_data[g][chart_id].keys()):
                print("ERROR:", g, "has measured different sizes to",
                      grader_one, "for chart", chart_id)
                print(grader_one, "=",
                      sorted(icc_data[grader_one][chart_id].keys()))
                print(g, "=", sorted(icc_data[g][chart_id].keys()))
                icc_data_good = False

        all_sizes = sorted(icc_data[grader_one][chart_id].keys())

        for g in sorted(icc_data.keys()):
            for s in all_sizes:
                icc_data_matrix[g].append(mean(icc_data[g][chart_id][s]))

    if not icc_data_good:
        sys.exit()

    # Convert to a Pandas data frame so we can do the ICC calculations.
    icc_df = pd.DataFrame(icc_data_matrix)

    # ...and convert to long format.
    icc_df['index'] = icc_df.index
    icc_df = pd.melt(icc_df, id_vars=['index'], value_vars=list(icc_df)[:-1])

    icc = pg.intraclass_corr(icc_df, 'index', 'variable', 'value')
    icc = icc.set_index("Type")
    print()
    print("=== ICC2 ===")
    print(icc.loc["ICC2"])
    print()

    # Find instances where there is disagreement by more than 2px.
    bad_data = False
    for chart, data0 in height_px.items():
            for lr, data1 in data0.items():
                for height in (X_HEIGHT, CAP_HEIGHT):
                    if height not in data1:
                        continue

                    if max(data1[height]) - min(data1[height]) > \
                    mean(data1[height]) * args.max_height_diff:
                        bad_data = True
                        print("ERROR: diff of more than", args.max_height_diff,
                              "for", chart, lr, height, ":", data1[height])

    if bad_data:
        sys.exit(1)

    # Extract the cap height / x-height ratio from the largest available font
    # size. Also deduce the line spacing.
    for chart, data0 in height_px.items():
        chart_id = float(chart.split(" :: ")[0])
        cap_ratio_lograd = None
        cap_ratio = None

        for lr in reversed(sorted(data0.keys())):
            if X_HEIGHT not in data0[lr] or CAP_HEIGHT not in data0[lr]:
                continue

            cap_ratio_lograd = lr
            break

        if cap_ratio_lograd is None:
            print("WARN: not enough data to calculate",
                  "cap height / x-height ratio for", chart)
            continue

        cap_ratio = mean(data0[cap_ratio_lograd][X_HEIGHT])\
                        / mean(data0[cap_ratio_lograd][CAP_HEIGHT])

        # Now that we have the ratio, go back and deduce the x-heights.
        for lr in reversed(sorted(data0.keys())):
            if X_HEIGHT in data0[lr] or CAP_HEIGHT not in data0[lr]:
                continue

            data0[lr][X_HEIGHT] = [mean(data0[lr][CAP_HEIGHT]) * cap_ratio]
            print("Deducing chart", chart_id, lr, "x-height =",
                  data0[lr][X_HEIGHT][0])

        # This is the x-height to full height ratio for Helvetica and Times
        # New Roman. Using these as surrogates for [sans]-serif fonts.
        x_height_ratio = (0.523 if SERIF_CHART[chart_id] else 0.450)

        # Line spacing.
        line_spacings = []
        for lr in reversed(sorted(data0.keys())):
            px_values = {"x": data0[lr][BOTTOM_X_VALUE],
                         "y": data0[lr][BOTTOM_Y_VALUE]}
            x_height = mean(data0[lr][X_HEIGHT])
            full_height = x_height / x_height_ratio
            cap_height = x_height / cap_ratio

            # Line spacing will be at least 1, so we can separate this way.
            # Take all of the values between 1 and 2 times full_height as
            # characters from the next line.
            first_line_y = min(px_values["y"])
            first_line_chars = [[],[]]
            second_line_chars = [[],[]]
            for idx, _ in enumerate(px_values["x"]):
                val = {"x": px_values["x"][idx],
                       "y": px_values["y"][idx]}

                if val["y"] < first_line_y + cap_height:
                    first_line_chars[0].append(val["x"])
                    first_line_chars[1].append(val["y"])
                elif val["y"] < first_line_y + (2 * cap_height):
                    second_line_chars[0].append(val["x"])
                    second_line_chars[1].append(val["y"])

            if len(second_line_chars[0]) > 0:
                # Because the page will have some amount of tilt, we linearly
                # regress the values and compare the y-intercepts.
                # This doesn't work if there aren't enough datapoints.
                line_spacing = None
                if len(set(first_line_chars[0])) <= 3 or\
                   len(set(second_line_chars[0])) <= 3 or True: # FIXME
                    line_spacing = (mean(second_line_chars[1])\
                        - mean(first_line_chars[1])) / full_height
                else:
                    first_line_reg = linregress(*first_line_chars)
                    second_line_reg = linregress(*second_line_chars)

                    # Use the distance between the lines at the midway point
                    # of the smallest subset as the line spacing.
                    midpoint_x = mean((max(first_line_chars[1]),
                                       min(first_line_chars[1])))
                    if len(second_line_chars) < len(first_line_chars):
                        midpoint_x = mean((max(second_line_chars[1]),
                                           min(second_line_chars[1])))

                    first_line_y = (first_line_reg.slope * midpoint_x) +\
                        first_line_reg.intercept
                    second_line_y = (second_line_reg.slope * midpoint_x) +\
                        second_line_reg.intercept
                    line_spacing = (second_line_y - first_line_y) / full_height

                line_spacings.append(line_spacing)

        print("Line spacing for chart", chart_id,
              "min=", round(min(line_spacings), 2),
              "max=", round(max(line_spacings), 2),
              "median=", round(median(line_spacings), 2))

    # These data will be used for the scatterplot.
    scatter_data = {SCATTER_LABEL: [],
                    SCATTER_X: [],
                    SCATTER_Y: [],
                    ERROR: []}

    # Run stats on the data.
    for chart, sizes in height_px.items():
        chart_id = float(chart.split(" :: ")[0])

        # Filter by chart ID.
        if args.chart_ids is not None and chart_id not in args.chart_ids:
            continue

        # Filter by font type.
        if args.font_type == "sans-serif" and SERIF_CHART[chart_id]:
            continue
        elif args.font_type == "serif" and not SERIF_CHART[chart_id]:
            continue

        # Optionally exclude new charts.
        if args.exclude_new and chart_id in NEW_CHARTS:
            continue

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
                if measure_type not in (BOTTOM_X_VALUE, BOTTOM_Y_VALUE):
                    print("  ", measure_type, " mean: ", round(mean_mm, 3),
                        "mm (", round(mean_mm - MEASUREMENT_ERROR, 3), "-",
                        round(mean_mm + MEASUREMENT_ERROR, 3), ")",
                        sep="")

                if measure_type == X_HEIGHT:
                    expected_mm = lograd_to_mm(lograd)
                    err = (mean_mm / expected_mm) - 1
                    err_min = ((mean_mm - MEASUREMENT_ERROR) / expected_mm) - 1
                    err_max = ((mean_mm + MEASUREMENT_ERROR) / expected_mm) - 1
                    tolerance = 0.05 if lograd > -0.2 else 0.1

                    marker = ""
                    if abs(err) > tolerance and abs(err_min) > tolerance and abs(err_max) > tolerance:
                        marker = "<<<<======= OUT OF TOLERANCE!"

                    print("    expected: ", round(expected_mm, 3), "mm",
                          sep="")
                    print("    error: ", round(err * 100, 2), "% ", marker,
                          sep="")

                    scatter_data[SCATTER_LABEL].append(chart)
                    scatter_data[SCATTER_X].append(lograd)
                    scatter_data[SCATTER_Y].append(err * 100)
                    scatter_data[ERROR].append(MEASUREMENT_ERROR / expected_mm * 100)

            if X_HEIGHT in means and CAP_HEIGHT in means:
                print(" ", X_HEIGHT, CAP_HEIGHT, "ratio:",
                      means[X_HEIGHT] / means[CAP_HEIGHT])

    # Sanity checking.
    assert(len(scatter_data[SCATTER_X]) == len(scatter_data[SCATTER_Y]))
    assert(len(scatter_data[SCATTER_X]) == len(scatter_data[SCATTER_LABEL]))
    assert(len(scatter_data[SCATTER_X]) == len(scatter_data[ERROR]))

    if lograd_xheight_csv is not None:
        with open(lograd_xheight_csv, 'w') as ofile:
            print(*['"' + k + '"' for k in scatter_data.keys()],
                  sep=",", file=ofile)

            for i in range(len(scatter_data[SCATTER_X])):
                print('"' + scatter_data[SCATTER_LABEL][i] + '"',
                      round(scatter_data[SCATTER_X][i], 3),
                      scatter_data[SCATTER_Y][i],
                      sep=",", file=ofile)

    # Generate the plot
    plt.rcParams.update({'font.size': 14})
    markers = ("o", "x", "s")
    assert(ceil(len(set(scatter_data[SCATTER_LABEL])) / 10) <= len(markers))

    for label_num, label in enumerate(sorted(set(scatter_data[SCATTER_LABEL]))):
        plot_data = [[], [], []]

        for i in range(len(scatter_data[SCATTER_X])):
            if scatter_data[SCATTER_LABEL][i] == label:
                plot_data[0].append(scatter_data[SCATTER_X][i])
                plot_data[1].append(scatter_data[SCATTER_Y][i])
                plot_data[2].append(scatter_data[ERROR][i])


        marker = markers[int(label_num / 10)]
        plt.errorbar(plot_data[0], plot_data[1], yerr=plot_data[2],
                    fmt=marker, label="Chart " + label.split(" :: ")[0],
                    markersize=15)

    plt.xlim(min(scatter_data[SCATTER_X]) - 0.1, max(scatter_data[SCATTER_X]) + 0.1)
    plt.xticks(np.arange(plt.axis()[0], plt.axis()[1], 0.1))
    plt.xlabel("Letter size (logRAD)")
    plt.ylabel("Size error (%)")
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), fancybox=True, ncol=7)
    plt.subplots_adjust(bottom=0.2)
    plt.title(args.chart_title)

    plt.axhline(y=0, color='b', linewidth=1)
    plt.fill_between(np.linspace(-0.15, plt.axis()[1], 2),
                     -5, +5, color="blue", alpha=0.2, label="Tolerance", linewidth=0)
    plt.fill_between(np.linspace(plt.axis()[0], -0.15, 2),
                     -10, +10, color="blue", alpha=0.2, label="Tolerance", linewidth=0)
    plt.show()

# EOF
