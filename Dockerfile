FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY bootstrap.py ./
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--log-level", "debug", "--host", "0.0.0.0", "--port", "8000"]
# RUN PYTHONPATH=. python app/main.py
