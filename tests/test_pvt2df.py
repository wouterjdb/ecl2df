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
