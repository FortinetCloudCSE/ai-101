FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-seed the SQLite database (same data as the agent image).
RUN python seed_db.py

EXPOSE 8000

CMD ["python", "server.py"]
