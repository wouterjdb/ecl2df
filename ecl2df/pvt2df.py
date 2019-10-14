# -*- coding: utf-8 -*-
"""
Extract the PVT data from an Eclipse (input) deck as Pandas Dataframes

Data can be extracted from a full Eclipse deck (*.DATA)
or from individual files.

Note that when parsing from individual files, it is
undefined in the syntax how many saturation functions (SATNUMs) are
present. For convenience, it is possible to estimate the count of
SATNUMs, but whenever this is known, it is recommended to either supply
TABDIMS or to supply the satnumcount directly to avoid possible bugs.

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
import argparse
import numpy as np
import pandas as pd

import sunbeam

from ecl2df import inferdims
from .eclfiles import EclFiles


KEYWORD_COLUMNS = {
    'DENSITY': ['PVTNUM', 'OILDENSITY', 'WATERDENSITY', 'GASDENSITY'],
    'PVTW': ['PVTNUM', 'PRESSURE', 'VOLUMEFACTOR', 'COMPRESSIBILITY', 'VISCOSITY', 'VISCOSIBILITY'],
    'PVTO': ['PVTNUM', 'GOR', 'PRESSURE', 'VOLUMEFACTOR', 'VISCOSITY'],
    'PVTG': ['PVTNUM', 'PRESSURE', 'RV', 'VOLUMEFACTOR', 'VISCOSITY'],
    'PVDG': ['PVTNUM', 'PRESSURE', 'VOLUMEFACTOR', 'VISCOSITY'],
    'ROCK': ['PVTNUM', 'PRESSURE', 'COMPRESSIBILITY']
    }


def inject_ntpvt(deckstr, ntpvt):
    """Insert a TABDIMS with NTPVT into a deck

    This is simple string manipulation, not sunbeam
    deck manipulation (which might be possible to do).

    Arguments:
        deckstr (str): A string containing a partial deck (f.ex only
            the SWOF keyword).
        ntpvt (int): The number for NTPVT to use in TABDIMS
            (this function does not care if it is correct or not)
    Returns:
        str: New deck with TABDIMS prepended.
    """
    if "TABDIMS" in deckstr:
        logging.warning("Not inserting TABDIMS in a deck where already exists")
        return deckstr
    return "TABDIMS\n 1* " + str(ntpvt) + " /\n\n" + str(deckstr)



# The following three functions can be refactored to 1..
def pvtwdeck2df(deck):
    pvtw_columns = KEYWORD_COLUMNS["PVTW"]
    pvtw_df = pd.DataFrame(columns=pvtw_columns)
    pvtnum = 0
    for deckrecord in deck['PVTW']:
        pvtnum += 1
        pvtw_row = {
            pvtw_columns[0]: int(pvtnum),
            pvtw_columns[1]: deckrecord[0][0],
            pvtw_columns[2]: deckrecord[1][0],
            pvtw_columns[3]: deckrecord[2][0],
            pvtw_columns[4]: deckrecord[3][0],
            pvtw_columns[5]: deckrecord[4][0],
            }
        pvtw_df = pvtw_df.append(pvtw_row, ignore_index=True)
    return pvtw_df

def densitydeck2df(deck, pvtnumcount=None):
    if "TABDIMS" not in deck:
        if not isinstance(deck, str):
            logging.critical("Can't guess NTPVT from a parsed deck without TABDIMS")
            pvtnumcount = 1
        if not pvtnumcount:
            pvtnum_estimate = inferdims.guess_dim(deck, "TABDIMS", 1)
            logging.warning("Guessed NPTVT=%s", str(pvtnum_estimate))
            augmented_strdeck = inferdims.inject_dimcount(str(deck), "TABDIMS", 1, pvtnum_estimate)
            deck = EclFiles.str2deck(augmented_strdeck)

    density_columns = KEYWORD_COLUMNS["DENSITY"]
    density_df = pd.DataFrame(columns=density_columns)
    pvtnum = 0
    for deckrecord in deck['DENSITY']:
        pvtnum += 1
        density_row = {
            density_columns[0]: int(pvtnum),
            density_columns[1]: deckrecord[0][0],
            density_columns[2]: deckrecord[1][0],
            density_columns[3]: deckrecord[2][0],
            }
        density_df = density_df.append(density_row, ignore_index=True)
    return density_df

def rockdeck2df(deck):
    rock_columns = KEYWORD_COLUMNS['ROCK']
    rock_df = pd.DataFrame(columns=rock_columns)
    pvtnum = 0
    for deckrecord in deck['ROCK']:
        pvtnum += 1
        rock_row = {
            rock_columns[0]: int(pvtnum),
            rock_columns[1]: deckrecord[0][0],
            rock_columns[2]: deckrecord[1][0],
            }
        rock_df = rock_df.append(rock_row, ignore_index=True)
    return rock_df


def deck2df(deck, satnumcount=None):
    """Extract the data in the saturation function keywords as a Pandas
    DataFrame.

    Data for all saturation functions are merged into one dataframe.
    The two first columns in the dataframe are 'KEYWORD' (which can be
    SWOF, SGOF, etc.), and then SATNUM which is an index counter from 1 and
    onwards. Then follows the data for each individual keyword that
    is found in the deck.

    SATNUM data can only be parsed correctly if TABDIMS is present
    and stating how many saturation functions there should be.
    If you have a string with TABDIMS missing, you must supply
    this as a string to this function, and not a parsed deck, as
    the default parser in EclFiles is very permissive (and only
    returning the first function by default).

    Arguments:
        deck (sunbeam.deck or str): Incoming data deck. Always
            supply as a string if you don't know TABDIMS-NTSFUN.
        satnumcount (int): Number of SATNUMs defined in the deck, only
            needed if TABDIMS with NTSFUN is not found in the deck.
            If not supplied (or None) and NTSFUN is not defined,
            it will be attempted inferred.

    Return:
        pd.DataFrame, columns 'SW', 'KRW', 'KROW', 'PC', ..
    """
    if "TABDIMS" not in deck:
        if not isinstance(deck, str):
            logging.critical(
                "Will not be able to guess NTPVT from a parsed deck without TABDIMS."
            )
            logging.critical(
                (
                    "Only data for first PVT region will be returned."
                    "Instead, supply string to deck2df()"
                )
            )
            ntpvt = 1
        # If TABDIMS is in the deck, NTPVT always has a value. It will
        # be set to 1 if defaulted.
        if not ntpvt:
            logging.warning(
                "TABDIMS+NTPVT or ntpvt not supplied. Will be guessed."
            )
            ntpvt_estimate = inferdims.guess_dim(deck, "TABDIMS", inferdims.NTPVT_POS)
            augmented_strdeck = inferdims.inject_dimcount(
                str(deck), "TABDIMS", inferdims.NTPVT_POS, ntpvt_estimate
            )
            # Re-parse the modified deck:
            deck = EclFiles.str2deck(augmented_strdeck)

        else:
            augmented_strdeck = inferdims.inject_dimcount(
                str(deck), "TABDIMS", inferdims.NTPVT_POS, satnumcount
            )
            # Re-parse the modified deck:
            deck = EclFiles.str2deck(augmented_strdeck)

    frames = []
    # Custom code for each keyword
    density_df = densitydeck2df(deck)

    for keyword in KEYWORD_COLUMNS.keys():
        if keyword in deck:
            pvtregion = 1
            for deckrecord in deck[keyword]:
                # All data for an entire PVTis returned in one list
                data = np.array(deckrecord[0])
                # Split up into the correct number of columns
                column_count = len(KEYWORD_COLUMNS[keyword])
                if len(data) % column_count:
                    logging.error("Inconsistent data length or bug")
                    return
                satpoints = int(len(data) / column_count)
                df = pd.DataFrame(
                    columns=KEYWORD_COLUMNS[keyword],
                    data=data.reshape(satpoints, column_count),
                )
                df["SATNUM"] = satnum
                df["KEYWORD"] = keyword
                df = df[["KEYWORD", "SATNUM"] + KEYWORD_COLUMNS[keyword]]
                satnum += 1
                frames.append(df)

    nonempty_frames = [frame for frame in frames if not frame.empty]
    if nonempty_frames:
        return pd.concat(nonempty_frames, axis=0, sort=False)
    logging.warning("No saturation data found in deck")
    return pd.DataFrame()


def fill_parser(parser):
    """Set up sys.argv parsers.

    Arguments:
        parser (ArgumentParser or subparser): parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE", help="Name of Eclipse DATA file or file with saturation functions."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file.",
        default="satfuncs.csv",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def main():
    """Entry-point for module, for command line utility
    """
    logging.warning("pvt2csv is deprecated, use 'ecl2csv pvt <args>' instead")
    parser = argparse.ArgumentParser()
    parser = fill_parser(parser)
    args = parser.parse_args()
    pvt2df_main(args)


def pvt2df_main(args):
    """Entry-point for module, for command line utility"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    if "TABDIMS" in deck:
        # Things are easier when a full deck with correct TABDIMS
        # is supplied:
        pvt_df = deck2df(deck)
    else:
        # When TABDIMS is not present, the code will try to infer
        # the number of saturation functions, this is necessarily
        # more error-prone:
        stringdeck = "".join(open(args.DATAFILE).readlines())
        pvt_df = deck2df(stringdeck)
    if not pvt_df.empty:
        logging.info(
            "Unique PVTNUM: %d, pvt keywords: %s",
            len(satfunc_df["PVTNUM"].unique()),
            str(satfunc_df["KEYWORD"].unique()),
        )
        pvt_df.to_csv(args.output, index=False)
        print("Wrote to " + args.output)
