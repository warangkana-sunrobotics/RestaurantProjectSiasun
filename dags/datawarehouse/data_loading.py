#!/usr/bin/env python3
#
# Copyright (C) 2026 
#			Written by 
#
########################################################
#
#	STANDARD IMPORTS
#

import json

import os

from datetime import date

from pathlib import Path

import logging

########################################################
#
#	LOCAL IMPORTS
#



########################################################
#
#	GLOBALS
#

logger = logging.getLogger( __name__ )

# <project root>/data ( /opt/airflow/data in the container ), override with RT_DATA_DIR
DATA_DIR = Path( os.getenv( "RT_DATA_DIR", Path( __file__ ).resolve().parents[2] / "data" ) )

########################################################
#
#	HELPER FUNCTIONS
#

def load_data( data_date=None ):
    data_date = data_date or date.today()
    file_path = DATA_DIR / f"RT_data_{data_date}.json"
    try:
        logger.info( f"Processing file: RT_data_{data_date}" )

        with open( file_path, "r", encoding="utf-8" ) as raw_data:
            data = json.load( raw_data )

        return data
    except FileNotFoundError:
        logger.error( f"File not found:{file_path}" )
        raise
    except json.JSONDecodeError:
        logger.error( f"Invalid JSON in file: {file_path}" )
        raise


########################################################
#
#	EXCEPTION DEFINITIONS
#



########################################################
#
#   MAIN DEFINITIONS
#

