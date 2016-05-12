#!/usr/bin/env python2.7

import argparse
import csv
import os.path
import pefile
import peutils
import re
import sys


if __name__ == "__main__":
    peid_sigs = "./userdb.txt"

    ## Parse options
    arg_parser = argparse.ArgumentParser()

    ## Don't output a CSV header line
    arg_parser.add_argument(
        "--no-header",
        action="store_true",
        default=False,
        help="don't output CSV header"
    )

    ## Delete invalid PE files
    arg_parser.add_argument(
        "--delete-invalid",
        action="store_true",
        default=False,
        help="delete invalid PE files"
    )

    ## Show only invalid PE files
    arg_parser.add_argument(
        "--only-invalid",
        action="store_true",
        default=False,
        help="show only invalid PE files"
    )

    ## Show only valid PE files
    arg_parser.add_argument(
        "--only-valid",
        action="store_true",
        default=False,
        help="show only valid PE files"
    )

    (args, params) = arg_parser.parse_known_args()
    data = []

    if not sys.stdin.isatty():
        data = [s.strip() for s in sys.stdin.readlines()]

    else:
        if len(sys.argv) > 1:
            data = [s.strip() for s in params]

    csv_writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
    output_header = args.no_header

    for f in data:
        if os.path.isfile(f):
            try:
                pe = pefile.PE(f, fast_load=True)
            except pefile.PEFormatError, e:
                if args.delete_invalid:
                    try:
                        os.unlink(f)
                    except:
                        pass

                continue

            is_valid = "Y"
            matches = []
            is_known = 0
            warnings = pe.get_warnings()

            if len(warnings) > 0:
                for w in warnings:
                    if re.search("(?:points beyond the end of the file|SizeOfRawData is larger than file.)", w):
                        is_valid = "N"
                        break

                    if re.search("IMAGE_SCN_MEM_WRITE and IMAGE_SCN_MEM_EXECUTE are set", w):
                        ## Known warning; skip it
                        is_known += 1

                if is_valid == "Y" and is_known < len(warnings):
                    print warnings

            else:
                sigs = peutils.SignatureDatabase(peid_sigs)
                matches = sigs.match(pe, ep_only=True) or []


            if not output_header:
                csv_writer.writerow(["filename","is_valid","signatures"])
                output_header = True

            if is_valid == "N":
                if args.delete_invalid:
                    try:
                        os.unlink(f)
                    except:
                        pass

                if args.only_valid is False:
                    csv_writer.writerow([f, is_valid, "|".join(matches)])

            else:
                if args.only_invalid is False:
                    csv_writer.writerow([f, is_valid, "|".join(matches)])


