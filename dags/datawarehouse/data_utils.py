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

def create_schema( schema ):
    conn, cur = get_conn_cursor()
    schema_sql = f"CREATE SCHEMA IF NOT EXISTS {schema};"
    cur.execute( schema_sql )
    conn.commit()
    close_conn_cursor( conn, cur )


def create_table( schema ):
    conn, cur = get_conn_cursor()
    if schema == "staging":
        table_sql = f"""
                CREATE TABLE IF NOT EXISTS {schema}.{table} (
                    "table_id" INT PRIMARY KEY NOT NULL,
                    "menu" VARCHAR(25)
                    "cost" INT 
                );
            """
    if schema == "core":
        table_sql = f"""
                CREATE TABLE IF NOT EXISTS {schema}.{table} (
                    "table_id" INT PRIMARY KEY NOT NULL,
                    "menu" VARCHAR(25)
                    "cost" INT 
                );
            """
    cur.execute( table_sql )
    conn.commit()
    close_conn_cursor( conn, cur )

def get_data_from_all_table( cur, schema ):
    cur.execute(f"""SELECT "table_id" FROM {schema}.{table}; """)
    ids = cur.fetchall()
    table_id = [row["table_id"] for row in ids]
    return table_id


########################################################
#
#	EXCEPTION DEFINITIONS
#



########################################################
#
#   MAIN DEFINITIONS
#

