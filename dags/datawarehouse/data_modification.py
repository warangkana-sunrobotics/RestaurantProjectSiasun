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
    if schema not in ("staging", "core"):
        raise ValueError(f"Unknown schema: {schema}")
    try:
        cur.execute(
            f"""
            INSERT INTO {schema}.{table}("order_id","table_id","menu","cost")
            VALUES (%(order_id)s, %(table_id)s, %(menu)s, %(cost)s)
            ON CONFLICT ("order_id") DO NOTHING;
            """,
            row,
        )
        conn.commit()
        logger.info(f"Inserted row with order_id: {row['order_id']}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting row with order_id: {row.get('order_id')} - {e}")
        raise e

def delete_rows(cur, conn, schema, ids_to_delete):
    if schema not in ("staging", "core"):
        raise ValueError(f"Unknown schema: {schema}")
    try:
        cur.execute(
            f"""
            DELETE FROM {schema}.{table}
            WHERE "order_id" = ANY(%s);
            """,
            (list(ids_to_delete),),
        )
        conn.commit()
        logger.info(f"Deleted rows with order_ids: {ids_to_delete}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deleting rows with order_ids: {ids_to_delete} - {e}")
        raise e



########################################################
#
#	EXCEPTION DEFINITIONS
#



########################################################
#
#   MAIN DEFINITIONS
#


