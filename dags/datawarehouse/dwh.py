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

from datawarehouse.data_utils import get_conn_cursor, close_conn_cursor, create_schema, create_table, get_data_from_all_table

from datawarehouse.data_modification import insert_rows, delete_rows

from datawarehouse.data_loading import load_data

########################################################
#
#	GLOBALS
#

logger = logging.getLogger(__name__)

table = "rt_api"

########################################################
#
#	HELPER FUNCTIONS
#

@task
def staging_table():
    schema = "staging"
    conn, cur = None, None
    try:
        # Prepare for the postgres database
        conn, cur = get_conn_cursor()

        # Load data from the json file due today()
        RT_data = load_data()

        # Create the storage and the table
        create_schema( schema )
        create_table( schema )

        for row in RT_data:
            insert_rows( cur, conn, schema, row )

        logger.info( f"{schema} table create complete " )

    except Exception as e:
        logger.error( f"An error occurred during the update of { schema } table: { e }" )
        raise e

    finally:
        if conn and cur:
            close_conn_cursor( conn,cur )


########################################################
#
#	EXCEPTION DEFINITIONS
#



########################################################
#
#   MAIN DEFINITIONS
#

