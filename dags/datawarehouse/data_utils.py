#!/usr/bin/env python3
#
# Copyright (C) 2026 
#			Written by 
#
########################################################
#
#	STANDARD IMPORTS
#

from airflow.providers.postgres.hooks.postgres import PostgresHook

from psycopg2.extras import RealDictCursor


########################################################
#
#	LOCAL IMPORTS
#



########################################################
#
#	GLOBALS
#

table = "rt_api"

########################################################
#
#	HELPER FUNCTIONS
#

def get_conn_cursor():
    hook = PostgresHook( postgres_conn_id="postgres_db_rt_elt", database="elt_db" )
    conn = hook.get_conn()
    cur = conn.cursor( cursor_factory=RealDictCursor )
    return conn, cur

def close_conn_cursor( conn, cur ):
    cur.close()
    conn.close()

def create_schema( conn, cur, schema ):
    schema_sql = f"CREATE SCHEMA IF NOT EXISTS {schema};"
    cur.execute( schema_sql )
    conn.commit()


def create_table( conn, cur, schema ):
    if schema not in ( "staging", "core" ):
        raise ValueError( f"Unknown schema: {schema}" )

    table_sql = f"""
            CREATE TABLE IF NOT EXISTS {schema}.{table} (
                "order_id" INT PRIMARY KEY NOT NULL,
                "table_id" INT NOT NULL,
                "menu" VARCHAR(255),
                "cost" REAL
            );
        """
    cur.execute( table_sql )
    conn.commit()

def get_data_from_all_table( cur, schema ):
    cur.execute(f"""SELECT "order_id" FROM {schema}.{table}; """)
    ids = cur.fetchall()
    order_ids = [row["order_id"] for row in ids]
    return order_ids


########################################################
#
#	EXCEPTION DEFINITIONS
#



########################################################
#
#   MAIN DEFINITIONS
#

