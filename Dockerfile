# Dockerfile for Governance AI - Document to Intelligent Checklist System

# Use the official Python base image
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files to disk
# and to ensure stdout/stderr is unbuffered
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default persistent storage locations (Render/containers typically mount /var/data)
ENV OUTPUT_DIR=/var/data/output
ENV CHROMA_PERSIST_DIR=/var/data/chroma_db
ENV DB_PATH=/var/data/output/governance_data.db
ENV HF_HOME=/var/data/hf
ENV TRANSFORMERS_CACHE=/var/data/hf/transformers

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
    && pip install --no-cache-dir -r requirements.txt

# Copy the entire project directory into the container
COPY . .

# Startup script: creates symlinks so app writes to persistent paths
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose ports for Streamlit and FastAPI
EXPOSE 8501 8000

# Entry point sets up persistent directories, then runs the passed command.
ENTRYPOINT ["docker-entrypoint.sh"]

# Default mode for deployments: run FastAPI.
# Platforms often provide PORT; we fall back to 8000.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
