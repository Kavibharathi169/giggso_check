# Dockerfile for Governance AI - Document to Intelligent Checklist System

# Use the official Python base image
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files to disk
# and to ensure stdout/stderr is unbuffered
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set the working directory
WORKDIR /app

# Install system dependencies (e.g., for Trafilatura or python-docx if needed)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir chromadb streamlit sentence-transformers

# Copy the entire project directory into the container
COPY . .

# Expose ports for Streamlit and FastAPI
EXPOSE 8501 8000

# Provide a default command.
# By default, we run the Streamlit app. For FastAPI, override in docker-compose.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
