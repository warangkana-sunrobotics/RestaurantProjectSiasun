ARG PYTHON_VERSION=3.10

FROM python:${PYTHON_VERSION}

WORKDIR /restaurantprojectsiasun/app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Solve the import dags in python file( from api.video_stats import ... )
ENV PYTHONPATH = /restaurantprojectsiasun/app/dags

# Similar run on the local pc
CMD ["fastapi", "run", "dags/api/API_write_data.py", "--host", "0.0.0.0", "--port", "8000" ]
