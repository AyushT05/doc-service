# Base Python image
FROM python:3.10-slim

# Install system dependencies (tesseract + libraries)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy your app files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Start command (modify if needed)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
