FROM python:3.11

WORKDIR /app

COPY . /app

RUN python -m venv venv \
    && . venv/bin/activate \
    && pip install --no-cache-dir -r requirements.txt \
    && alembic upgrade head

CMD . venv/bin/activate && python app/main.py
