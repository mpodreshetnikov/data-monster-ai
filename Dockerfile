FROM python:3.11

WORKDIR /app

COPY alembic.ini /app/alembic.ini
COPY . /app

RUN python -m venv venv \
    && . venv/bin/activate \
    && pip install --no-cache-dir -r requirements.txt

CMD . venv/bin/activate &&  alembic upgrade head && python app/main.py
