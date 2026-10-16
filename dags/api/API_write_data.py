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
import os
import secrets
import time
from collections import deque
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2 import sql

from dotenv import load_dotenv

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field, field_validator

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

# Load the .env only when It exists( on docker the variables come from env_file )
load_dotenv( dotenv_path = ENV_PATH )

logging.basicConfig( level = os.getenv( "LOG_LEVEL", "INFO" ) )
logger = logging.getLogger( __name__ )

TABLE_NAME = "orders"

MENU_TABLE = "menu"

SCHEMA_NAME = "public"

# Swagger( /docs ) is disabled by default because the customer must not see the API structure.
_enable_docs = os.getenv( "ENABLE_DOCS", "false" ).lower() == "true"

app = FastAPI(
    title = "Restaurant API",
    docs_url = "/docs" if _enable_docs else None,
    redoc_url = None,
    openapi_url = "/openapi.json" if _enable_docs else None,
)

# Number of tables in the restaurant( the web page has the same number in the dropdown )
TABLE_COUNT = int( os.getenv( "TABLE_COUNT", "5" ) )

# Rate limit per client IP per minute( public endpoints of the web page )
RATE_LIMIT_READ = int( os.getenv( "RATE_LIMIT_READ", "120" ) )
RATE_LIMIT_WRITE = int( os.getenv( "RATE_LIMIT_WRITE", "30" ) )

# The web page( index.html, script.js, style.css ) is served from the same origin, so CORS is not needed.
WEB_DIR = Path( os.getenv( "WEB_DIR", BASE_DIR / "web" ) )

# CORS : allow only the origins which was listed in CORS_ALLOW_ORIGINS( comma separated ). Empty = not allow any.
_origins = [ o.strip() for o in os.getenv( "CORS_ALLOW_ORIGINS", "" ).split( "," ) if o.strip() ]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins = _origins,
        allow_methods = [ "GET", "POST", "DELETE" ],
        allow_headers = [ "X-API-Key", "Content-Type" ],
    )

@app.middleware( "http" )
async def security_headers( request, call_next ):
    response = await call_next( request )
    response.headers.setdefault( "X-Content-Type-Options", "nosniff" )
    response.headers.setdefault( "X-Frame-Options", "DENY" )
    response.headers.setdefault( "Referrer-Policy", "no-referrer" )
    return response

########################################################
#
#	HELPER FUNCTIONS
#

@contextmanager
def get_db():
    '''
    Open the connection + cursor for 1 request and always close them( cursor first, then connection ).
    Commit when the block complete, rollback when the error happened.
    '''
    conn = psycopg2.connect(
        host = os.getenv( "DB_HOST", "localhost" ),            # <- change when It run in container( = service name in docker-compose.yml )
        dbname = os.getenv( "POSTGRES_CONN_DAILY_DB" ),
        user = os.getenv( "POSTGRES_CONN_DAILY_USERNAME" ),
        password = os.getenv( "POSTGRES_CONN_DAILY_PASSWORD" ),
        port = os.getenv( "POSTGRES_CONN_DAILY_PORT" ),
        connect_timeout = 5,
    )
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def convertIntoJson( column, output ):
    '''
    Parameters
    -------
    column: list
        The column of the postgres database ['order_id', 'table_id', 'menu', 'cost']

    output: list of tuple
        The value of all rows in the postgres database [(1, 1, "Hambuger", 500), (2, 2, "sausage", 100)]

    Returns
    -------
    data: list of dict
        The rows in form of json( cost was converted from Decimal to float )
    '''
    data = []
    for eachRow in output:
        row = dict( zip( column, eachRow ) )
        for key, value in row.items():
            if isinstance( value, Decimal ):
                row[ key ] = float( value )
            elif isinstance( value, ( datetime, date ) ):
                row[ key ] = value.isoformat()
        data.append( row )

    return data


def _table():
    return sql.SQL( "{}.{}" ).format( sql.Identifier( SCHEMA_NAME ), sql.Identifier( TABLE_NAME ) )


def _fetch( query, params = None ):
    with get_db() as cur:
        cur.execute( query, params )
        output = cur.fetchall()
        columns = [ desc[0] for desc in cur.description ]
    return convertIntoJson( columns, output )


def _db_error( action ):
    # Log the detail on the server only, the customer will get the general message.
    logger.exception( f"An error occurred during {action} on {SCHEMA_NAME}.{TABLE_NAME}" )
    return HTTPException( status_code = 500, detail = "Internal server error" )

# API key authentication( header X-API-Key ) -> fail closed if the server was not configured
_api_key_header = APIKeyHeader( name = "X-API-Key", auto_error = False )

def verify_api_key( provided : str = Security( _api_key_header ) ):
    expected = os.getenv( "API_KEY", "" )
    if not expected:
        logger.error( "API_KEY is not configured, reject every request" )
        raise HTTPException( status_code = 503, detail = "Service is not configured" )
    # compare_digest prevent the timing attack
    if not provided or not secrets.compare_digest( provided.encode(), expected.encode() ):
        raise HTTPException( status_code = 401, detail = "Invalid or missing API key" )

########################################################
#
#	CLASS DEFINITIONS
#

class OrderCreate( BaseModel ):
    table_id : int = Field( gt = 0, le = 9_999_999 )
    menu : str = Field( min_length = 1, max_length = 255 )
    cost : float = Field( ge = 0, lt = 100_000_000 )

    @field_validator( "menu" )
    @classmethod
    def menu_not_blank( cls, v : str ):
        v = v.strip()
        if not v:
            raise ValueError( "menu must not be blank" )
        return v

########################################################
#
#   MAIN DEFINITIONS
#

router = APIRouter( prefix = "/restaurant", dependencies = [ Depends( verify_api_key ) ] )

# 1. Select all the order which was "x" table.
@router.get( "/getOrders/{numTable}" )
def getOrderOnTable( numTable : int ):
    try:
        query = sql.SQL( "SELECT * FROM {} WHERE table_id = %s ORDER BY order_id;" ).format( _table() )
        return _fetch( query, ( numTable, ) )
    except Exception:
        raise _db_error( f"select table {numTable}" )

# 2. Select all the order which all table( paginated ).
@router.get( "/getOrders" )
def getAllOrder( limit : int = Query( 100, ge = 1, le = 1000 ), offset : int = Query( 0, ge = 0 ) ):
    try:
        query = sql.SQL( "SELECT * FROM {} ORDER BY order_id LIMIT %s OFFSET %s;" ).format( _table() )
        return _fetch( query, ( limit, offset ) )
    except Exception:
        raise _db_error( "select all" )

# 3. Add the order in database.
@router.post( "/insertOrder", status_code = 201 )
def insertOrderDatabase( orderUser : OrderCreate ):
    try:
        # order_id is generated by the database( identity ), so it never duplicate after restart.
        query = sql.SQL(
            "INSERT INTO {} ( table_id, menu, cost ) VALUES ( %s, %s, %s ) RETURNING order_id;"
        ).format( _table() )

        with get_db() as cur:
            cur.execute( query, ( orderUser.table_id, orderUser.menu, orderUser.cost ) )
            order_id = cur.fetchone()[0]

        logger.info( f"Insert the order into the database correctly, order_id = {order_id}" )
        return { "Message": "complete insert the order into database", "order_id": order_id }
    except Exception:
        raise _db_error( "insert" )

# 4. Delete the order which was using the order_id.
@router.delete( "/delOrders/orderId/{idOrder}" )
def deleteOrderId( idOrder : int ):
    try:
        query = sql.SQL( "DELETE FROM {} WHERE order_id = %s;" ).format( _table() )
        with get_db() as cur:
            cur.execute( query, ( idOrder, ) )
            deleted = cur.rowcount
    except Exception:
        raise _db_error( f"delete order {idOrder}" )

    if deleted == 0:
        raise HTTPException( status_code = 404, detail = f"order {idOrder} not found" )

    logger.info( f"Delete the orderId from the database which was id = {idOrder}" )
    return { "Message": f"complete delete order : {idOrder}" }

# 5. Delete the order on the table.
@router.delete( "/delOrders/tableId/{idTable}" )
def deleteTableId( idTable : int ):
    try:
        query = sql.SQL( "DELETE FROM {} WHERE table_id = %s;" ).format( _table() )
        with get_db() as cur:
            cur.execute( query, ( idTable, ) )
            deleted = cur.rowcount
    except Exception:
        raise _db_error( f"delete table {idTable}" )

    if deleted == 0:
        raise HTTPException( status_code = 404, detail = f"no order in table {idTable}" )

    logger.info( f"Delete all the orders in the tableId from the database which was table = {idTable}, rows = {deleted}" )
    return { "Message": f"complete delete all orders in table : {idTable}", "deleted": deleted }

app.include_router( router )

########################################################
#
#   WEB PAGE API( /api/* ) : customer ordering page
#   - menu / order / bill are public( the customer has no key ) but rate limited
#   - price and name always come from the menu table, never from the client
#   - checkout( close the bill ) needs the staff API key
#

_rate_hits = {}

def rate_limit( bucket, limit ):
    def dependency( request : Request ):
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        if len( _rate_hits ) > 10_000:
            # Drop the stale IPs so the memory can not grow without limit
            for k in [ k for k, q in _rate_hits.items() if not q or now - q[-1] > 60 ]:
                del _rate_hits[ k ]
        hits = _rate_hits.setdefault( ( ip, bucket ), deque() )
        while hits and now - hits[0] > 60:
            hits.popleft()
        if len( hits ) >= limit:
            raise HTTPException( status_code = 429, detail = "Too many requests, please try again later",
                                 headers = { "Retry-After": "60" } )
        hits.append( now )
    return dependency


def table_id_from( tableNo : str ):
    n = int( tableNo )
    if n < 1 or n > TABLE_COUNT:
        raise HTTPException( status_code = 422, detail = f"table must be 1-{TABLE_COUNT}" )
    return n


class OrderItem( BaseModel ):
    menuId : int = Field( gt = 0, le = 1_000_000 )
    quantity : int = Field( ge = 1, le = 99 )


class WebOrder( BaseModel ):
    tableNo : str = Field( pattern = r"^\d{1,3}$" )
    items : list[ OrderItem ] = Field( min_length = 1, max_length = 50 )


class Checkout( BaseModel ):
    tableNo : str = Field( pattern = r"^\d{1,3}$" )


web = APIRouter( prefix = "/api" )

def _menu_table():
    return sql.SQL( "{}.{}" ).format( sql.Identifier( SCHEMA_NAME ), sql.Identifier( MENU_TABLE ) )

# W1. Menu for the page( only the available items )
@web.get( "/menu", dependencies = [ Depends( rate_limit( "read", RATE_LIMIT_READ ) ) ] )
def webMenu():
    try:
        query = sql.SQL(
            "SELECT menu_id AS id, name, price, category, emoji AS img FROM {} WHERE available ORDER BY menu_id;"
        ).format( _menu_table() )
        return _fetch( query )
    except Exception:
        raise _db_error( "select menu" )

# W2. Send the order of 1 round( price / name are taken from the menu table )
@web.post( "/orders", status_code = 201, dependencies = [ Depends( rate_limit( "write", RATE_LIMIT_WRITE ) ) ] )
def webCreateOrder( order : WebOrder ):
    table_id = table_id_from( order.tableNo )

    # Merge the duplicate menuId so the same menu is 1 line
    wanted = {}
    for item in order.items:
        wanted[ item.menuId ] = wanted.get( item.menuId, 0 ) + item.quantity
    if any( q > 99 for q in wanted.values() ):
        raise HTTPException( status_code = 422, detail = "quantity per menu must not exceed 99" )

    try:
        with get_db() as cur:
            cur.execute(
                sql.SQL( "SELECT menu_id, name, price FROM {} WHERE menu_id = ANY( %s ) AND available;" ).format( _menu_table() ),
                ( list( wanted ), )
            )
            found = { r[0]: ( r[1], r[2] ) for r in cur.fetchall() }

            unknown = sorted( set( wanted ) - set( found ) )
            if unknown:
                raise HTTPException( status_code = 400, detail = f"menu not available: {unknown}" )

            insert = sql.SQL(
                "INSERT INTO {} ( table_id, menu, cost, menu_id, quantity ) VALUES ( %s, %s, %s, %s, %s ) RETURNING order_id;"
            ).format( _table() )

            order_ids, total = [], Decimal( 0 )
            for menu_id, qty in wanted.items():
                name, price = found[ menu_id ]
                cur.execute( insert, ( table_id, name, price, menu_id, qty ) )
                order_ids.append( cur.fetchone()[0] )
                total += Decimal( price ) * qty
    except HTTPException:
        raise
    except Exception:
        raise _db_error( f"web order table {table_id}" )

    logger.info( f"Web order table {table_id}: {len(order_ids)} lines, total {total}" )
    return { "message": "order received", "orderIds": order_ids, "roundTotal": float( total ) }

# W3. All unpaid lines of the table( for the bill )
@web.get( "/orders/table/{tableNo}", dependencies = [ Depends( rate_limit( "read", RATE_LIMIT_READ ) ) ] )
def webTableBill( tableNo : str ):
    if not tableNo.isdigit() or len( tableNo ) > 3:
        raise HTTPException( status_code = 422, detail = "invalid table" )
    table_id = table_id_from( tableNo )
    try:
        # Old rows without menu_id get the negative id so they are not merged together
        query = sql.SQL(
            """
            SELECT COALESCE( menu_id, -order_id ) AS "menuId", menu AS name, cost AS price, quantity
            FROM {} WHERE table_id = %s AND status = 'open' ORDER BY order_id;
            """
        ).format( _table() )
        return _fetch( query, ( table_id, ) )
    except Exception:
        raise _db_error( f"select bill table {table_id}" )

# ---- PromptPay QR( EMV QRCPS ) : the server builds the payload so the real account never goes to the browser code ----
# Default is a FAKE test account( phone 0800000000 ), set PROMPTPAY_ID in .env for the real one
PROMPTPAY_ID = os.getenv( "PROMPTPAY_ID", "0800000000" )

def _emv( tag, value ):
    return f"{tag}{len( value ):02d}{value}"

def _crc16( text ):
    # CRC-16/CCITT-FALSE( poly 0x1021, init 0xFFFF ) over the payload including the "6304" tag
    crc = 0xFFFF
    for byte in text.encode( "ascii" ):
        crc ^= byte << 8
        for _ in range( 8 ):
            crc = ( ( crc << 1 ) ^ 0x1021 if crc & 0x8000 else crc << 1 ) & 0xFFFF
    return f"{crc:04X}"

def promptpay_payload( account, amount = None ):
    digits = "".join( c for c in account if c.isdigit() )
    if len( digits ) == 10:                       # mobile number -> 0066 + number without the leading 0
        target = _emv( "01", "0066" + digits[1:] )
    elif len( digits ) == 13:                     # national id / tax id
        target = _emv( "02", digits )
    else:
        raise ValueError( "PROMPTPAY_ID must be a 10 digits phone or a 13 digits id" )

    body = _emv( "00", "01" ) + _emv( "01", "12" if amount else "11" )      # 12 = dynamic( one time ), 11 = static
    body += _emv( "29", _emv( "00", "A000000677010111" ) + target )
    body += _emv( "53", "764" ) + _emv( "58", "TH" )                        # currency THB, country TH
    if amount:
        body += _emv( "54", f"{Decimal( amount ):.2f}" )
    body += "6304"
    return body + _crc16( body )

# W4. QR payload of the table with the amount of its unpaid bill
@web.get( "/orders/table/{tableNo}/qr", dependencies = [ Depends( rate_limit( "read", RATE_LIMIT_READ ) ) ] )
def webTableQr( tableNo : str ):
    if not tableNo.isdigit() or len( tableNo ) > 3:
        raise HTTPException( status_code = 422, detail = "invalid table" )
    table_id = table_id_from( tableNo )
    try:
        rows = _fetch(
            sql.SQL( "SELECT cost * quantity AS amount FROM {} WHERE table_id = %s AND status = 'open';" ).format( _table() ),
            ( table_id, )
        )
    except Exception:
        raise _db_error( f"select qr table {table_id}" )

    total = sum( ( Decimal( str( r[ "amount" ] ) ) for r in rows ), Decimal( 0 ) )
    if total <= 0:
        raise HTTPException( status_code = 404, detail = f"table {table_id} has no unpaid order" )
    return { "amount": float( total ), "payload": promptpay_payload( PROMPTPAY_ID, total ) }

# W5. Close the bill of the table( STAFF ONLY: needs X-API-Key )
@web.post( "/orders/checkout", dependencies = [ Depends( verify_api_key ), Depends( rate_limit( "write", RATE_LIMIT_WRITE ) ) ] )
def webCheckout( body : Checkout ):
    table_id = table_id_from( body.tableNo )
    try:
        with get_db() as cur:
            cur.execute(
                sql.SQL(
                    "UPDATE {} SET status = 'paid', paid_at = now() WHERE table_id = %s AND status = 'open' RETURNING cost * quantity;"
                ).format( _table() ),
                ( table_id, )
            )
            amounts = [ r[0] for r in cur.fetchall() ]
    except Exception:
        raise _db_error( f"checkout table {table_id}" )

    if not amounts:
        raise HTTPException( status_code = 404, detail = f"table {table_id} has no unpaid order" )

    total = sum( amounts )
    logger.info( f"Checkout table {table_id}: {len(amounts)} lines, total {total}" )
    return { "message": "paid", "lines": len( amounts ), "total": float( total ) }

app.include_router( web )

# Health check( no authentication, no data ) for docker / load balancer
@app.get( "/health" )
def health():
    return { "status": "ok" }

# Serve the customer web page at "/" ( must be the last, after every API route )
if WEB_DIR.is_dir():
    app.mount( "/", StaticFiles( directory = WEB_DIR, html = True ), name = "web" )
