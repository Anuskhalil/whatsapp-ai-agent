FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app


# ---------------------------------
# PYTHON DEPENDENCIES
# ---------------------------------

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt


# ---------------------------------
# APPLICATION
# ---------------------------------

COPY app ./app
COPY start.py ./start.py


# ---------------------------------
# RUNTIME DIRECTORIES
# ---------------------------------

RUN mkdir -p /app/logs


# ---------------------------------
# FASTAPI PORT
# ---------------------------------

EXPOSE 8000


# ---------------------------------
# PRODUCTION COMMAND
# ---------------------------------

CMD ["python", "start.py"]