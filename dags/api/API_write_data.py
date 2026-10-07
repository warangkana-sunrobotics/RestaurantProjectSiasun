#!/usr/bin/env python3
#
# Copyright (C) 2026 
#			Written by 
#
########################################################
#
#	STANDARD IMPORTS
#

from fastapi import FastAPI

import psycopg2

import os

from dotenv import load_dotenv

from pathlib import Path

import logging

import json

from pydantic import BaseModel

########################################################
#
#	LOCAL IMPORTS
#



########################################################
#
#	GLOBALS
#

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"

logger = logging.getLogger(__name__)

TABLE_NAME = "orders"

SCHEMA_NAME = "public"

global NEXT_ID
NEXT_ID = 1

app = FastAPI()

########################################################
#
#	HELPER FUNCTIONS
#

load_dotenv( dotenv_path = ENV_PATH )

def get_conn_cursor():
    conn = psycopg2.connect(
        dbname=f"{os.getenv("POSTGRES_CONN_DAILY_DB")}",
        user=f"{os.getenv("POSTGRES_CONN_DAILY_USERNAME")}",
        password=f"{os.getenv("POSTGRES_CONN_DAILY_PASSWORD")}",
        host="localhost",
        port=f"{os.getenv("POSTGRES_CONN_DAILY_PORT")}"
    )
    cur = conn.cursor()
    return conn, cur


def close_conn_cursor(conn, cur):
    conn.close()
    cur.close()

def convertIntoJson( column, output ):
    '''
    Parameters
    -------
    column: list
        The column of the postgres database ['order_id', 'table_id', 'menu', 'cost']

    output: tuple
        The value of all rows in the postgres database [(1, 1, "Hambuger", 500), (2, 2, "sausage", 100), (3, 1, "Water", 50)]

    Returns
    -------
    json_str: json type
        The output in form of json file
    '''  

    data = []
    for eachRow in output:
        data.append(dict(zip(column, eachRow)))
   
    return data

########################################################
#
#	CLASS DEFINITIONS
#

class OrderCreate( BaseModel ):
    table_id : int
    menu : str
    cost : float

########################################################
#
#   MAIN DEFINITIONS
#

# # 1. Select all the order which was "x" table.
@app.get( "/restaurant/getOrders/{numTable}" )
def getOrderOnTable( numTable : int ):
    conn, cur = None, None
    try:
        conn, cur = get_conn_cursor()

        select_sql = f'''
        SELECT *
        FROM {SCHEMA_NAME}.{TABLE_NAME}
        WHERE table_id = {numTable};
        '''

        cur.execute(select_sql)
        output = cur.fetchall()
        columns = [ desc[0] for desc in cur.description ]

        logger.info( f"Select all the information from the database" )

        result = convertIntoJson( columns, output )
        return result

        ## If you want to get in form of json you can comment "return result" and uncomment below 2 rows.
        # json_str = json.dumps( result )
        # return json_str
        
    except Exception as e:
        logger.error(f"An error occurred during the Select on table: {numTable} of {SCHEMA_NAME}:{TABLE_NAME} raise {e}")
        raise e
    
    finally:
        if conn and cur:
            close_conn_cursor( conn, cur )

# 2. Select all the order which all table.
@app.get( "/restaurant/getOrders" )
def getAllOrder():
    conn, cur = None, None
    try:
        conn, cur = get_conn_cursor()

        select_sql = f'''
        SELECT *
        FROM {SCHEMA_NAME}.{TABLE_NAME};
        '''

        cur.execute(select_sql)
        output = cur.fetchall()
        columns = [ desc[0] for desc in cur.description ]

        logger.info( f"Select all the information from the database" )

        result = convertIntoJson( columns, output )
        return result

        ## If you want to get in form of json you can comment "return result" and uncomment below 2 rows.
        # json_str = json.dumps( result )
        # return json_str

    except Exception as e:
        logger.error(f"An error occurred during the Select all of {SCHEMA_NAME}:{TABLE_NAME} raise {e}")
        raise e
    
    finally:
        if conn and cur:
            close_conn_cursor( conn, cur )

# 3. Add the order in database.
@app.post( "/restaurant/insertOrder" )
def insertOrderDatabase( orderUser : OrderCreate ):
    conn, cur = None, None
    try:
        global NEXT_ID
        
        conn, cur = get_conn_cursor()

        tableId = orderUser.table_id
        menu = orderUser.menu
        cost = orderUser.cost

        insert_sql = f'''
        INSERT INTO {SCHEMA_NAME}.{TABLE_NAME} ( order_id, table_id, menu, cost )
        VALUES
            ( {NEXT_ID}, {tableId}, '{menu}', {cost} );
        '''

        cur.execute( insert_sql )
        conn.commit()

        logger.info( f"Insert the order into the database correctly" )

        NEXT_ID += 1
        
        return { "Message": f"complete insert the order into database" }

    except Exception as e:
        logger.error( f"An error occurred during the insert orders in {SCHEMA_NAME}:{TABLE_NAME} raise {e}" )
        raise e
    
    finally:
        if conn and cur:
            close_conn_cursor( conn, cur )

# 4. Delete the order which was using the order_id.
@app.delete( "/restaurant/delOrders/orderId/{idOrder}" )
def deleteOrderId( idOrder : int ):
    conn, cur = None, None
    try:
        conn, cur = get_conn_cursor()

        delete_sql = f'''
        DELETE FROM {SCHEMA_NAME}.{TABLE_NAME}
        WHERE order_id = {idOrder};
        '''

        cur.execute( delete_sql )
        conn.commit()

        logger.info( f"Delelt the orderId from the database which was id = { idOrder }" )

        return { "Message": f"complete delete order : {idOrder}" }

    except Exception as e:
        logger.error(f"An error occurred during the delete some of {SCHEMA_NAME}:{TABLE_NAME} raise {e}")
        raise e
        
    finally:
        if conn and cur:
            close_conn_cursor( conn, cur )

# 5. Delete the order on the table.
@app.delete( "/restaurant/delOrders/tableId/{idTable}" )
def deleteTableId( idTable : int ):
    conn, cur = None, None
    try:
        conn, cur = get_conn_cursor()

        delete_sql = f'''
        DELETE FROM {SCHEMA_NAME}.{TABLE_NAME}
        WHERE table_id = {idTable};
        '''

        cur.execute( delete_sql )
        conn.commit()

        logger.info( f"Delte all the orders in the tableId from the database which was table = {idTable}" )

        return { "Message": f"complete delete all orders in tabel : {idTable}" }

    except Exception as e:
        logger.error(f"An error occurred during the delete all of {SCHEMA_NAME}:{TABLE_NAME} raise {e}")
        raise e

    finally:
        if conn and cur:
            close_conn_cursor( conn, cur )
