# Set base image (Python 3.11-slim)
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --fix-missing \
    --no-install-recommends \
    wget \
    ca-certificates \
    curl && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*


# Copy and install Python dependencies
COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

COPY entrypoint.sh .

RUN chmod +x ./entrypoint.sh

# Copy the rest of the application files to the working directory
COPY . .

# Expose port
EXPOSE 8080

CMD ["./entrypoint.sh"]