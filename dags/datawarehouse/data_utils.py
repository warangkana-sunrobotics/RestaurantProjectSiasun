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

from airflow.providers.postgres.hooks.postgres import PostgresHook

from psycopg2 import sql

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

# Must match AIRFLOW_CONN_POSTGRES_DB_RT_ELT in airflow.yml
CONN_ID = "postgres_db_rt_elt"

# The schema name is put into the SQL as identifier, so allow only the known names.
ALLOWED_SCHEMAS = ( "staging", "core" )

########################################################
#
#	HELPER FUNCTIONS
#

def check_schema( schema ):
    if schema not in ALLOWED_SCHEMAS:
        raise ValueError( f"Unknown schema: {schema}" )
    return schema


def get_conn_cursor():
    hook = PostgresHook( postgres_conn_id = CONN_ID )
    conn = hook.get_conn()
    cur = conn.cursor()
    return conn, cur


def close_conn_cursor( conn, cur ):
    cur.close()
    conn.close()


def create_schema( cur, schema ):
    check_schema( schema )
    cur.execute( sql.SQL( "CREATE SCHEMA IF NOT EXISTS {};" ).format( sql.Identifier( schema ) ) )


def create_table( cur, schema ):
    '''
    staging and core use the same structure.
    The order_id come from the source database, so it is the primary key( 1 table can have many orders ).
    '''
    check_schema( schema )
    cur.execute(
        sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {}.{} (
                order_id  BIGINT PRIMARY KEY,
                table_id  BIGINT        NOT NULL,
                menu      VARCHAR(255)  NOT NULL,
                cost      NUMERIC(10,2) NOT NULL,
                loaded_at TIMESTAMPTZ   NOT NULL DEFAULT now()
            );
            """
        ).format( sql.Identifier( schema ), sql.Identifier( table ) )
    )


def get_data_from_all_table( cur, schema ):
    check_schema( schema )
    cur.execute( sql.SQL( "SELECT order_id FROM {}.{};" ).format( sql.Identifier( schema ), sql.Identifier( table ) ) )
    return [ row[0] for row in cur.fetchall() ]


########################################################
#
#	EXCEPTION DEFINITIONS
#



########################################################
#
#   MAIN DEFINITIONS
#

