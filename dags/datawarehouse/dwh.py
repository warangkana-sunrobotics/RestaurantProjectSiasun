#!/usr/bin/env python3
#
# Copyright (C) 2026
#			Written by
#
########################################################
#
#	STANDARD IMPORTS
#

import logging

from airflow.decorators import task

########################################################
#
#	LOCAL IMPORTS
#

from datawarehouse.data_utils import get_conn_cursor, close_conn_cursor, create_schema, create_table

from datawarehouse.data_modification import upsert_rows, truncate_table, promote_staging_to_core

from datawarehouse.data_loading import load_data

########################################################
#
#	GLOBALS
#

logger = logging.getLogger( __name__ )

########################################################
#
#	HELPER FUNCTIONS
#

@task
def staging_table( ds = None ):
    '''Load the json file of the day into staging( staging = mirror of the file, so it is truncated first ).'''
    schema = "staging"
    conn, cur = None, None
    try:
        rows = load_data( ds )

        conn, cur = get_conn_cursor()

        create_schema( cur, schema )
        create_table( cur, schema )

        # Everything in 1 transaction: if any row is bad, the old staging data is kept.
        truncate_table( cur, schema )
        count = upsert_rows( cur, schema, rows )
        conn.commit()

        logger.info( f"{schema} table load complete: {count} rows" )

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error( f"An error occurred during the update of {schema} table: {e}" )
        raise

    finally:
        if conn and cur:
            close_conn_cursor( conn, cur )


@task
def core_table():
    '''Clean + upsert staging into core.'''
    schema = "core"
    conn, cur = None, None
    try:
        conn, cur = get_conn_cursor()

        create_schema( cur, schema )
        create_table( cur, schema )

        count = promote_staging_to_core( cur )
        conn.commit()

        logger.info( f"{schema} table load complete: {count} rows" )

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error( f"An error occurred during the update of {schema} table: {e}" )
        raise

    finally:
        if conn and cur:
            close_conn_cursor( conn, cur )


########################################################
#
#	EXCEPTION DEFINITIONS
#



########################################################
#
#   MAIN DEFINITIONS
#

