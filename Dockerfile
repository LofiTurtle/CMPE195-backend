FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

COPY . .

EXPOSE 8000

ENV FLASK_APP=server

RUN echo "#!/bin/bash \
\nflask db upgrade && \
\ngunicorn backend:app -w 4 -b 0.0.0.0:8000" > start.sh

RUN chmod +x start.sh

CMD ["./start.sh"]