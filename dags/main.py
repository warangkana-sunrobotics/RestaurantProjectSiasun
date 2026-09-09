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

from datawarehouse.dwh import staging_table

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
    "max_active_runs": 1,
    "dagrun_timeout": timedelta(hours=1),
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
    description = "DAG inserted data into both staging schemas",
    schedule=None,
    catchup=False
) as dag:

    # Define tasks
    update_staging = staging_table()

    # Define dependencies
    update_staging