FROM python:3.11

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install python-oracledb fastapi uvicorn

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
