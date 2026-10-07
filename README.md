# This project was realated to restaurant 

### This project was create by 

1. Kongphop Tongedee

2. Warangkana Makhasawat

## How to use the database

1. Git pull the lastest version

2. On the project directory run "docker compose up -d"

3. Get inside the API directory by "cd /dags/api"

4. Run "fastapi dev API_write_data.py" ( In the future, I will deploy on the docker to run with the container in docker )

5. Use the api by following the API postgres topic

# Common command [appendix]

## Docker command

- docker ps 
: show all the container_id, image, command, created, status, ports, and names which was running. 

- docker exec it [ Name container ] bash
: Execute into the container bash while using the docker.

- psql -U [ Name user which define in the .env file ] -d [ Name db which define in the .env file ]
: connenct to the database and execute in the postgress database

caution

1. If using the "docker compose up -d" with old connection config -> need to delete the old volume before start up again. The command for delete the old volume "docker compose down -v"

2. Not sure, The meaning of POSTGRES_DB, and POSTGRES_NAME wasn't the same in the docker-compose.yml

## Postgres SQL command

- 

caution

1. The command from INSERT INTO public.orders ( order_id, table_id, menu, cost ) VALUES ( 0, 1, 'Icecream', 75 ); 
: If we use the "" the postgresSQL will asume as the column, it will get the error. Need to use '' for assign the text. 

2. The port connect inside the container of postgresSQL alway 5432, so in the docker-compose.yaml need to change only the port in front of [port which can be change]:5432 in the enviroment topic.

## Pytest command 

## API postgres

- [ localhost ]/restaurant/getOrders
: Select all the order which all table.

- [ localhost ]/restaurant/getOrders/[ table Id ]
: Select all the order which was select table id.

- [ localhost ]/restaurant/delOrders/orderId/[ order Id ]
: Delete only the order id which match in the api

- [ localhost ]/restaurant/delOrders/tableId/[ table Id ]
: Delete all the order which in the table id

- [ localhost ]/restaurant/insertOrder
: Insert the order into the database which was follow the json type

Example of use

1. http://127.0.0.1:8000/restaurant/getOrders -> Test by using postman with GET method

2. http://127.0.0.1:8000/restaurant/getOrders/2 -> Test by using postman with GET method

3. http://127.0.0.1:8000/restaurant/delOrders/orderId/0 -> Test by using postman with DELETE method

4. http://127.0.0.1:8000/restaurant/delOrders/tableId/1 -> Test by using postman with DELETE method

5. http://127.0.0.1:8000/restaurant/insertOrder -> Test by using postman with POST method

Select Body praser and use raw to insert the information of json type( like this : {
    "table_id": 3,
    "menu": "Hamburger",
    "cost": 100
} )
