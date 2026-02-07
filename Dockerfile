# Use a lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# Install system dependencies (needed for PDF processing and OpenCV)
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Create uploads folder
RUN mkdir -p uploads && chmod 777 uploads

# Expose the port
EXPOSE 8080

# Start command
CMD uvicorn app:app --host 0.0.0.0 --port $PORT
