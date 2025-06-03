FROM python:3.9-slim
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY app.py /app/app.py
COPY adjust_brightness.py /app/adjust_brightness.py
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]