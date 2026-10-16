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
import logging
import os
from pathlib import Path

########################################################
#
#	LOCAL IMPORTS
#



########################################################
#
#	GLOBALS
#

logger = logging.getLogger( __name__ )

# dags/datawarehouse/data_loading.py -> parents[2] = project root( /opt/airflow in container )
DATA_DIR = Path( os.getenv( "RT_DATA_DIR", Path( __file__ ).resolve().parents[2] / "data" ) )

########################################################
#
#	HELPER FUNCTIONS
#

def load_data( ds ):
    '''
    Parameters
    -------
    ds: str
        The logical date of the DAG run( YYYY-MM-DD ), the file name is RT_data_<ds>.json
        Use the logical date instead of date.today() so the re-run / backfill read the right file.
    '''
    file_path = DATA_DIR / f"RT_data_{ds}.json"
    try:
        logger.info( f"Processing file: {file_path.name}" )

        with open( file_path, "r", encoding = "utf-8" ) as raw_data:
            data = json.load( raw_data )

        if not isinstance( data, list ):
            raise ValueError( f"{file_path} must contain the list of orders" )

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

