#!/usr/bin/env python
# Take one or more chart scans and calculate the contrast.
# Written by Tim Murphy <tim.murphy@canberra.edu.au> 2026

import argparse
import cv2
import os

# Calculate the contrast using the Weber formula:
#   C = (L_bg - L_fg) / L_bg
def calc_contrast(background: int, foreground: int):
    return (background - foreground) / background

# Gamma correction using the standard formula: y = x^2.2
# Note: need to convert to a decimal first, and will return a normalised value.
def gamma_correction(x):
    return pow(x/255.0, 2.2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--chart_img", nargs="+", type=str, required=True,
                        help="Scanned image(s) of reading chart(s).")
    parser.add_argument("--gauss_kernel_size", type=int, default=9,
                        help="Gaussian kernel size. Must be positive and odd.")
    args = parser.parse_args()

    # Validate command line arguments.
    for chart in args.chart_img:
        if not os.path.isfile(chart):
            raise ValueError("Invalid chart file: " + chart)

    if args.gauss_kernel_size < 1 or args.gauss_kernel_size % 2 == 0:
        raise ValueError("Gaussian kernel size must be positive and odd.")

    # For each image, perform the following:
    #   1. Convert to grayscale.
    #   2. Apply Gaussian filtering.
    #   3. Find darkest and lightest pixels.
    #   4. Print the pixel values and locations, and calculated contrast.
    print("filename", "dark_val", "light_val", "dark_val_x", "dark_val_y",
          "light_val_x", "light_val_y", "weber_contrast", sep=",")
    for chart in args.chart_img:
        img = cv2.imread(chart, cv2.IMREAD_GRAYSCALE)
        img = cv2.GaussianBlur(img, [args.gauss_kernel_size] * 2, 0)

        dark_val, light_val, dark_loc, light_loc = cv2.minMaxLoc(img)

        # Apply gamma correction.
        dark_val = gamma_correction(dark_val)
        light_val = gamma_correction(light_val)

        print(chart, dark_val, light_val, *dark_loc, *light_loc,
              calc_contrast(light_val, dark_val), sep=",")

# EOF
