#!/usr/bin/env python3
#
# Copyright (C) 2026 
#			Written by 
#
########################################################
#
#	STANDARD IMPORTS
#

from airflow import DAG

import pendulum

from datetime import datetime, timedelta

########################################################
#
#	LOCAL IMPORTS
#

from datawarehouse.dwh import staging_table, core_table

########################################################
#
#	GLOBALS
#

# Define the local timezone
local_tz = pendulum.timezone("Asia/Bangkok")

# Default Args
default_args = {
    "owner": "dataengineers",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "email": "data@engineers.com",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 9, 8, tzinfo=local_tz),
}

########################################################
#
#	HELPER FUNCTIONS
#



########################################################
#
#	EXCEPTION DEFINITIONS
#



########################################################
#
#   MAIN DEFINITIONS
#

with DAG(
    dag_id="update_db",
    default_args = default_args,
    description = "DAG load the RT_data_<date>.json into staging, then clean + upsert into core",
    # Run every day at 01:00 Bangkok time( the file of the day must be placed in ./data before this time )
    schedule="0 1 * * *",
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=1),
) as dag:

    # Define tasks
    update_staging = staging_table()
    update_core = core_table()

    # Define dependencies
    update_staging >> update_core