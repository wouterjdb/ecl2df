# -*- coding: utf-8 -*-
"""Test module for pvt2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd
import numpy as np
import logging

from ecl2df import pvt2df, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")

logger = logging.getLogger("")
logger.setLevel(logging.DEBUG)


def test_densitydeck2df():
    eclfiles = EclFiles(DATAFILE)
    density_df = pvt2df.densitydeck2df(eclfiles.get_ecldeck())
    assert len(density_df) == 1
    assert 'PVTNUM' in density_df
    assert 'OILDENSITY' in density_df
    assert 'WATERDENSITY' in density_df
    assert 'GASDENSITY' in density_df

    two_pvtnum_deck = """DENSITY
        860      999.04       1.1427 /
        800      950     1.05
        /
        """
    density_df = pvt2df.densitydeck2df(EclFiles.str2deck(two_pvtnum_deck))
    # (a warning will be printed that we cannot guess)
    assert len(density_df) == 1
    density_df = pvt2df.densitydeck2df(two_pvtnum_deck)
    print(density_df)
    assert 'PVTNUM' in density_df
    assert density_df['PVTNUM'].max() == 2
    assert density_df['PVTNUM'].min() == 1
    assert 'OILDENSITY' in density_df


def test_pvt2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    pvtdf = pvt2df.pvt2df(eclfiles)

    assert not pvtdf.empty
    assert len(pvtdf.columns)


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-pvt.csv"
    sys.argv = ["pvt2csv", DATAFILE, "-o", tmpcsvfile]
    pvt2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)


def test_main_subparsers():
    """Test command line interface"""
    tmpcsvfile = ".TMP-pvt.csv"
    sys.argv = ["ecl2csv", "pvt", DATAFILE, "-o", tmpcsvfile]
    ecl2csv.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    os.remove(tmpcsvfile)
