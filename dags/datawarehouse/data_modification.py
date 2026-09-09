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


########################################################
#
#	LOCAL IMPORTS
#



########################################################
#
#	GLOBALS
#

logger = logging.getLogger( __name__ )

table = "rt_api"

########################################################
#
#	HELPER FUNCTIONS
#

def insert_rows(cur, conn, schema, row):
    try:
        if schema == "staging":
            table_id = "table_id"
            cur.execute(
                f"""
                INSERT INTO {schema}.{table}("table_id","menu","cost")
                VALUES (%(table_id)s, %(menu)s, %(cost)s);
                """,
                row,
            )
        elif schema == "core":
            table_id = "table_id"
            cur.execute(
                f"""
                INSERT INTO {schema}.{table}("table_id","menu","cost")
                VALUES (%(table_id)s, %(menu)s, %(cost)s);
                """,
                row,
            )
        conn.commit()
        logger.info(f"Inserted row with table_id: { row[table_id]}")
    except Exception as e:
        logger.error(f"Error inserting row with talbe_id: {row[table_id]}")
        raise e

def delete_rows(cur, conn, schema, id_to_delete):
    try:
        cur.execute(
            f"""
            DELETE FROM {schema}.{table}
            WHERE "Video_ID" IN {id_to_delete};
            """
        )
        conn.commit()
        logger.info(f"Deleted rows with Video_IDs: {id_to_delete}")
    except Exception as e:
        logger.error(f"Error deleting rows with Video_IDs: {id_to_delete} - {e}")
        raise e



########################################################
#
#	EXCEPTION DEFINITIONS
#



########################################################
#
#   MAIN DEFINITIONS
#


