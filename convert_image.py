# Convert one or more chart images into black and white (not greyscale) so that
# the text can be measured without subjectivity.
# Written by Tim Murphy <tim.murphy@canberra.edu.au> 2025

import argparse
import cv2
import os
import sys

if __name__ == '__main__':
    ADAPTIVE_C_DEFAULT = 2
    THRESHOLD_DEFAULT = 224
    TYPE_DEFAULT = "adaptive"
    BLOCK_DEFAULT = 51

    # argparse check for positive numbers.
    def block_size_int(i):
        if int(i) <= 0:
            raise argparse.ArgumentTypeError(
                "Block size must be odd and greater than 1")
        return int(i)

    parser = argparse.ArgumentParser()
    parser.add_argument("--input_img", nargs="*", type=str, default=[],
                        help="One or more input image files.")
    parser.add_argument("--input_dir", required=False, type=str,
                        help="Directory of input image files (non-recursive).")
    parser.add_argument("--output_dir", required=True, type=str,
                        help="Directory to save output files. Will overwrite.")
    parser.add_argument("--type", required=False, type=str,
                        default=TYPE_DEFAULT, choices=("exact", "adaptive"),
                        help="Threshold type: 'exact' will use the " +
                             "--threshold value to determine the threshold, " +
                             "'adaptive' will do a Gaussian adaptive " +
                             "threshold of size --block_size. Default: " +
                             TYPE_DEFAULT + ".")
    parser.add_argument("--threshold", required=False, type=int,
                        default=THRESHOLD_DEFAULT,
                        choices=range(0,256), metavar="[0-255]",
                        help="Threshold level [0-255] used for exact " +
                             "thresholding. Pixels greater than " +
                             "this value will become white, and the rest " +
                             " will become black. Default: " +
                             str(THRESHOLD_DEFAULT) + ".")
    parser.add_argument("--block_size", required=False, type=block_size_int,
                        default=BLOCK_DEFAULT,
                        help="Block size used for adaptive thresholding. " +
                             "Must be an odd number greater than 1. " +
                             "Default: " + str(BLOCK_DEFAULT) + ".")
    parser.add_argument("--adaptive_c", required=False, type=int,
                        default=ADAPTIVE_C_DEFAULT,
                        help="Constant value subtracted from the mean when " +
                             "performing adaptive thresholding. Default: " +
                             str(ADAPTIVE_C_DEFAULT) + ".")
                        
    args = parser.parse_args()

    # Additional error checking.
    for img in args.input_img:
        if not os.path.isfile(img):
            raise ValueError("--input_img does not exist: " + img)

    if (not args.input_dir is None) and (not os.path.isdir(args.input_dir)):
        raise ValueError("--input_dir does not exist: " + args.input_dir)

    if not os.path.exists(args.output_dir):
        print("Creating output directory " + args.output_dir + "...",
              end="", flush=True)
        os.makedirs(args.output_dir, exist_ok=True)
        print("done")
    elif os.path.isfile(args.output_dir):
        raise ValueError("--output_dir is not a directory: " + args.output_dir)

    # Collate the input files from --input_img and --input dir.
    img_files = args.input_img

    if not args.input_dir is None:
        img_files += [ os.path.join(args.input_dir, f)
                       for f in os.listdir(args.input_dir)
                       if os.path.isfile(os.path.join(args.input_dir, f)) ]

    if len(img_files) == 0:
        print("ERROR: no input images found.", file=sys.stderr)
        print()
        parser.print_help()
        sys.exit(1)

    # Convert the images.
    success = 0
    for img_file in img_files:
        print("Converting ", img_file, "...", sep="", end="", flush=True)
        img = cv2.imread(img_file, cv2.IMREAD_GRAYSCALE)

        if img is None:
            print("!!! invalid image file (ignoring) !!!")
            continue

        # Threshold the image.
        thresh = None
        if args.type == "exact":
            _, thresh = cv2.threshold(img, args.threshold,
                                      255, cv2.THRESH_BINARY)
        elif args.type == "adaptive":
            thresh = cv2.adaptiveThreshold(img, 255,
                                              cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY,
                                              args.block_size,
                                              args.adaptive_c)
        else:
            # This should never happen.
            raise ValueError("Invalid threshold type: " + args.type)

        # All done - write the image to disk.
        output_png = os.path.join(
            args.output_dir,
            os.path.splitext(os.path.split(img_file)[1])[0] + ".png")

        cv2.imwrite(output_png, thresh)

        success += 1
        print("done")

    print("Converted", success, "of", len(img_files), "input files.")

    print()
    print("All done! Have a nice day :)")

# EOF
