# -*- coding: utf-8 -*-
"""
Extract non-neighbour connection (NNC) information from Eclipse output files.
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
import argparse
import pandas as pd

from .eclfiles import EclFiles
from .grid import gridgeometry2df

logging.basicConfig()
logger = logging.getLogger(__name__)


def df(eclfiles, coords=False, pillars=False):
    """Produce a Pandas Dataframe with NNC information

    A NNC is a pair of cells that are not next to each other
    in the index space (I, J, K), and are associated to a
    non-zero transmissibility.

    Columns: I1, J1, K1 (first cell in cell pair)
    I2, J2, K2 (second cell in cell pair), TRAN (transmissibility
    between the two cells)

    Args:
        eclfiles (EclFiles): object that can serve EclFile and EclGrid
            on demand
        coords (boolean): Set to True if you want the midpoint of the two
            connected cells to be computed and added to the columns
            X, Y and Z.
        pillars (boolean): Set to True if you want to filter to vertical
            (along pillars) connections only.

    Returns:
        pd.DataFrame. Empty if no NNC information found.
    """
    egrid_file = eclfiles.get_egridfile()
    egrid_grid = eclfiles.get_egrid()
    init_file = eclfiles.get_initfile()

    if not ("NNC1" in egrid_file and "NNC2" in egrid_file):
        logger.warning("No NNC data in EGRID")
        return pd.DataFrame()

    # Grid indices for first cell in cell pairs, into a vertical
    # vector. The indices are "global" in libecl terms, and are
    # 1-based (FORTRAN). Convert to zero-based before sending to get_ijk()
    nnc1 = egrid_file["NNC1"][0].numpy_view().reshape(-1, 1)
    logger.info(
        "NNC1: len: %d, min: %d, max: %d (global indices)",
        len(nnc1),
        min(nnc1),
        max(nnc1),
    )
    idx_cols1 = ["I1", "J1", "K1"]
    nnc1_df = pd.DataFrame(
        columns=idx_cols1, data=[egrid_grid.get_ijk(global_index=x - 1) for x in nnc1]
    )
    # Returned indices from get_ijk are zero-based, convert to 1-based indices
    nnc1_df[idx_cols1] = nnc1_df[idx_cols1] + 1

    # Grid indices for second cell in cell pairs
    nnc2 = egrid_file["NNC2"][0].numpy_view().reshape(-1, 1)
    logger.info(
        "NNC2: len: %d, min: %d, max: %d (global indices)",
        len(nnc2),
        min(nnc2),
        max(nnc2),
    )
    idx_cols2 = ["I2", "J2", "K2"]
    nnc2_df = pd.DataFrame(
        columns=idx_cols2, data=[egrid_grid.get_ijk(global_index=x - 1) for x in nnc2]
    )
    nnc2_df[idx_cols2] = nnc2_df[idx_cols2] + 1

    # Obtain transmissibility value, corresponding to the cell pairs above.
    tran = init_file["TRANNNC"][0].numpy_view().reshape(-1, 1)
    logger.info(
        "TRANNNC: len: %d, min: %f, max: %f, mean=%f",
        len(tran),
        min(tran),
        max(tran),
        tran.mean(),
    )
    tran_df = pd.DataFrame(columns=["TRAN"], data=tran)

    nncdf = pd.concat([nnc1_df, nnc2_df, tran_df], axis=1)
    if pillars:
        nncdf = filter_vertical(nncdf)
    if coords:
        nncdf = add_nnc_coords(nncdf, eclfiles)
    return nncdf


def add_nnc_coords(nncdf, eclfiles):
    """Add columns X, Y and Z for the connection midpoint

    This extracts x, y and z for (I1, J1, K1) and (I2, J2, K2)
    and computes the average in each direction.

    Arguments:
        nncdf (DataFrame): With grid index columns (I1, J1, K1, I2, J2, K2)
        eclfiles (EclFiles): Object used to fetch grid data from EGRID.

    Returns:
        DataFrame: Incoming dataframe augmented with the columns X, Y and Z.
    """
    gridgeometry = gridgeometry2df(eclfiles)
    gnncdf = pd.merge(
        nncdf,
        gridgeometry,
        how="left",
        left_on=["I1", "J1", "K1"],
        right_on=["I", "J", "K"],
    )
    gnncdf = pd.merge(
        gnncdf,
        gridgeometry,
        how="left",
        left_on=["I2", "J2", "K2"],
        right_on=["I", "J", "K"],
        suffixes=("", "_2"),
    )
    # Use pd.DataFrame.mean for averaging, since it can ignore
    # NaN's. In case only one coordinate is NaN, we then get the other one.
    # (NaN coordinates are potentially from zero-volume cells?)
    gnncdf["X"] = gnncdf[["X", "X_2"]].mean(axis=1)
    gnncdf["Y"] = gnncdf[["Y", "Y_2"]].mean(axis=1)
    gnncdf["Z"] = gnncdf[["Z", "Z_2"]].mean(axis=1)

    # Let go of the temporary columns we have in gnncdf
    return gnncdf[list(nncdf.columns) + ["X", "Y", "Z"]]


def filter_vertical(nncdf):
    """Filter to vertical connections

    Arguments:
        nncdf (DataFrame): A dataframe with the columns
            I1, J1, K1, I2, J2, K2.

    Returns:
        Filtered copy of incoming dataframe.
    """
    prelen = len(nncdf)
    vnncdf = nncdf[nncdf["I1"] == nncdf["I2"]]
    vnncdf = vnncdf[vnncdf["J1"] == vnncdf["J2"]]
    postlen = len(vnncdf)
    logger.info(
        "Filtered to vertical connections, %d removed, %d connections kept",
        prelen - postlen,
        postlen,
    )
    return vnncdf


# Remaining functions are for the command line interface


def fill_parser(parser):
    """Set up sys.argv parser

    Arguments:
        parser: argparse.ArgumentParser or argparse.subparser
    """
    parser.add_argument(
        "DATAFILE",
        help="Name of Eclipse DATA file. " + "INIT and EGRID file must lie alongside.",
    )
    parser.add_argument(
        "-c",
        "--coords",
        action="store_true",
        help="Add xyz coords of connection midpoint",
    )
    parser.add_argument(
        "-p",
        "--pillars",
        "--vertical",
        action="store_true",
        help="Only dump vertical (along pillars) connections",
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Name of output csv file.", default="nnc.csv"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def main():
    """Entry-point for module, for command line utility

    It may become deprecated to have a main() function
    and command line utility for each module in ecl2df
    """
    logger.warning("nnc2csv is deprecated, use 'ecl2csv nnc <args>' instead")
    parser = argparse.ArgumentParser()
    fill_parser(parser)
    args = parser.parse_args()
    nnc2df_main(args)


def nnc2df_main(args):
    """Command line access point from main() or from ecl2csv via subparser"""
    if args.verbose:
        logger.setLevel(logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    nncdf = df(eclfiles, coords=args.coords, pillars=args.pillars)
    if nncdf.empty:
        logger.warning("Empty NNC dataframe being written to disk!")
    nncdf.to_csv(args.output, index=False)
    print("Wrote to " + args.output)
