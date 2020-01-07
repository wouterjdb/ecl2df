# pylint: disable=c0301

"""
Extract FIP region reports from Eclipse PRT file

Example block to extract data from:
                                                =================================
                                                : FIPZON  REPORT REGION    2    :
                                                :     PAV =        139.76  BARSA:
                                                :     PORV=     27777509.   RM3 :
                           :--------------- OIL    SM3  ---------------:-- WAT    SM3  -:--------------- GAS    SM3  ---------------:
                           :     LIQUID         VAPOUR         TOTAL   :       TOTAL    :       FREE      DISSOLVED         TOTAL   :
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :CURRENTLY IN PLACE       :     21091398.                    21091398.:       4590182. :           -0.    483594842.     483594842.
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :OUTFLOW TO OTHER REGIONS :        76266.                       76266.:         75906. :            0.      1818879.       1818879.
 :OUTFLOW THROUGH WELLS    :                                         0.:             0. :                                         0.
 :MATERIAL BALANCE ERROR.  :                                         0.:             0. :                                         0.
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :ORIGINALLY IN PLACE      :     21136892.                    21136892.:       4641214. :            0.    484657561.     484657561.
 :-------------------------:-------------------------------------------:----------------:-------------------------------------------:
 :OUTFLOW TO REGION   1    :       143128.                      143128.:       -161400. :            0.      3017075.       3017075.
 :OUTFLOW TO REGION   3    :       -66862.                      -66862.:        198900. :           -0.     -1198195.      -1198195.
 :OUTFLOW TO REGION   8    :            0.                           0.:         38405. :            0.            0.             0.
 ====================================================================================================================================


"""

import re
import sys
import logging
import datetime
import pandas as pd

from .eclfiles import EclFiles
from .common import parse_ecl_month

REGION_REPORT_COLUMNS = [
    "DATE",
    "FIPNAME",
    "REGION",
    "DATATYPE",
    "TO_REGION",
    "STOIIP_OIL",
    "ASSOCIATEDOIL_GAS",
    "STOIIP_TOTAL",
    "WATER_TOTAL",
    "GIIP_GAS",
    "ASSOCIATEDGAS_OIL",
    "GIIP_TOTAL",
]


def report_block_lineparser(line):
    """
    Parses single lines within region reports, splits data into a tuple.

    Does not support many different phase configurations yet.
    """

    allowed_line_starts = [" :CURRENTLY", " :OUTFLOW", " :MATERIAL", " :ORIGINALLY"]
    if not any([line.startswith(x) for x in allowed_line_starts]):
        return None

    colonsections = line.split(":")
    if "OUTFLOW TO REGION" in line:
        to_index = int(colonsections[1].split()[3])
        row_name = "OUTFLOW TO REGION"
    else:
        to_index = None
        row_name = colonsections[1].strip()
    # Oil section:
    if len(colonsections[2].split()) == 3:
        # yes we have:
        (liquid_oil, vapour_oil, total_oil) = map(float, colonsections[2].split())
    elif len(colonsections[2].split()) == 1:
        total_oil = float(colonsections[2])
        (liquid_oil, vapour_oil) = (None, None)
    else:
        (liquid_oil, total_oil) = map(float, colonsections[2].split())
        vapour_oil = None
    total_water = float(colonsections[3])

    # Gas section:
    if len(colonsections[4].split()) == 1:
        total_gas = float(colonsections[4])
        (free_gas, dissolved_gas) = (None, None)
    else:
        (free_gas, dissolved_gas, total_gas) = map(float, colonsections[4].split())
    return (
        row_name,
        to_index,
        liquid_oil,
        vapour_oil,
        total_oil,
        total_water,
        free_gas,
        dissolved_gas,
        total_gas,
    )


def df(prtfile, fipname="FIPNUM"):
    """
    Parses a PRT file from Eclipse and finds FIPXXXX REGION REPORT blocks and
    organizes those numbers into a dataframe

    Each row in the dataframe represents one parsed line in the PRT file, with
    DATE and region index added.

    Args:
        prtfile (string): filename
        fipname (string): The name of the regport regions, FIPNUM, FIPZON or whatever
            Max length of the string is 8, the first three characters must be FIP,
            and the next 3 characters must be unique for a given Eclipse deck.
    Returns:
        pd.DataFrame
    """
    if not fipname.startswith("FIP"):
        raise ValueError("fipname must start with FIP")
    if len(fipname) > 8:
        raise ValueError("fipname can be at most 8 characters")

    # List of rows in final dataframe
    records = []

    # State variables while parsing line by line:
    in_report_block = False
    region_index = None
    date = None

    datematcher = re.compile(r"\s\sREPORT\s+(\d+)\s+(\d+)\s+(\w+)\s+(\d+)")
    reportblockmatcher = re.compile(".+" + fipname + r"\s+REPORT\s+REGION\s+(\d+)")

    with open(prtfile) as prt_fh:
        for line in prt_fh:
            matcheddate = re.match(datematcher, line)
            if matcheddate:
                newdate = datetime.date(
                    year=int(matcheddate.group(4)),
                    month=parse_ecl_month(matcheddate.group(3)),
                    day=int(matcheddate.group(2)),
                )
                if newdate != date:
                    date = newdate
                    logging.info("Found date: %s", str(date))
                continue
            matchedreportblock = re.match(reportblockmatcher, line)
            if matchedreportblock:
                in_report_block = True
                region_index = int(matchedreportblock.group(1))
                logging.info("  Region report for region %s", str(region_index))
                continue
            if line.startswith(" ============================"):
                in_report_block = False
                continue

            if in_report_block:
                if line.startswith(" :") and not line.startswith(" :--"):
                    records.append(
                        [date, fipname, region_index]
                        + list(report_block_lineparser(line))
                    )

    return pd.DataFrame(data=records, columns=REGION_REPORT_COLUMNS)


def fill_parser(parser):
    """Fill parser with command line arguments"""
    parser.add_argument("PRTFILE", type=str, help="Eclipse PRT file (or DATA file)")
    parser.add_argument(
        "--fipname",
        type=str,
        help="Region parameter name of interest",
        default="FIPNUM",
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Output CSV filename", default="outflow.csv"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def fipreports_main(args):
    """Command line API"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    if args.PRTFILE.endswith(".PRT"):
        prtfile = args.PRTFILE
    else:
        prtfile = EclFiles(args.PRTFILE).get_prtfilename()
    dframe = df(prtfile, args.fipname)
    if args.output == "-":
        # Ignore pipe errors when writing to stdout.
        from signal import signal, SIGPIPE, SIG_DFL

        signal(SIGPIPE, SIG_DFL)
        dframe.to_csv(sys.stdout, index=False)
    else:
        logging.info("Writing output to disk")
        dframe.to_csv(args.output, index=False)
        print("Wrote to " + args.output)