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

from psycopg2 import sql

########################################################
#
#	LOCAL IMPORTS
#

from datawarehouse.data_utils import check_schema

########################################################
#
#	GLOBALS
#

logger = logging.getLogger( __name__ )

table = "rt_api"

REQUIRED_KEYS = ( "order_id", "table_id", "menu", "cost" )

########################################################
#
#	HELPER FUNCTIONS
#

def _qualified( schema ):
    return sql.SQL( "{}.{}" ).format( sql.Identifier( check_schema( schema ) ), sql.Identifier( table ) )


def validate_row( row ):
    '''Raise ValueError if the row is not complete / not valid, so the bad data never reach the warehouse.'''
    missing = [ k for k in REQUIRED_KEYS if k not in row or row[k] is None ]
    if missing:
        raise ValueError( f"Row {row} is missing: {missing}" )
    if float( row["cost"] ) < 0:
        raise ValueError( f"Row {row} has the negative cost" )
    return { k: row[k] for k in REQUIRED_KEYS }


def upsert_rows( cur, schema, rows ):
    '''Insert the rows, if order_id already exist update it( safe to run many times ).'''
    clean = [ validate_row( r ) for r in rows ]
    query = sql.SQL(
        """
        INSERT INTO {} ( order_id, table_id, menu, cost )
        VALUES ( %(order_id)s, %(table_id)s, %(menu)s, %(cost)s )
        ON CONFLICT ( order_id ) DO UPDATE
        SET table_id = EXCLUDED.table_id,
            menu = EXCLUDED.menu,
            cost = EXCLUDED.cost,
            loaded_at = now();
        """
    ).format( _qualified( schema ) )
    cur.executemany( query, clean )
    logger.info( f"Upserted {len(clean)} rows into {schema}.{table}" )
    return len( clean )


def truncate_table( cur, schema ):
    cur.execute( sql.SQL( "TRUNCATE TABLE {};" ).format( _qualified( schema ) ) )


def delete_rows( cur, schema, ids_to_delete ):
    ids = list( ids_to_delete )
    if not ids:
        return 0
    cur.execute( sql.SQL( "DELETE FROM {} WHERE order_id = ANY( %s );" ).format( _qualified( schema ) ), ( ids, ) )
    logger.info( f"Deleted {cur.rowcount} rows from {schema}.{table}" )
    return cur.rowcount


def promote_staging_to_core( cur ):
    '''Copy staging -> core. Only valid rows( cost >= 0, menu not blank ), menu is trimmed.'''
    cur.execute(
        sql.SQL(
            """
            INSERT INTO {core} ( order_id, table_id, menu, cost )
            SELECT order_id, table_id, btrim( menu ), cost
            FROM {staging}
            WHERE cost >= 0 AND length( btrim( menu ) ) > 0
            ON CONFLICT ( order_id ) DO UPDATE
            SET table_id = EXCLUDED.table_id,
                menu = EXCLUDED.menu,
                cost = EXCLUDED.cost,
                loaded_at = now();
            """
        ).format( core = _qualified( "core" ), staging = _qualified( "staging" ) )
    )
    logger.info( f"Promoted {cur.rowcount} rows from staging to core" )
    return cur.rowcount


########################################################
#
#	EXCEPTION DEFINITIONS
#



########################################################
#
#   MAIN DEFINITIONS
#

