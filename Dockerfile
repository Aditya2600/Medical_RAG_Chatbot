# Parent image
FROM python:3.10-slim

# Essential environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Work directory inside the docker container
WORKDIR /app

# Installing system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m appuser

# -------------------------
# Dependency install (cached)
# -------------------------
# Copy only dependency files first so Docker can cache pip layer
COPY pyproject.toml* poetry.lock* requirements.txt* setup.py* setup.cfg* ./

# Upgrade pip and install deps
# If requirements.txt exists -> install it
# Else if setup/pyproject exists -> install project
RUN pip install --no-cache-dir -U pip \
    && if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; \
       else pip install --no-cache-dir .; \
       fi \
    && pip install --no-cache-dir gunicorn

# Copy application code
COPY . .

# Ensure correct permissions
RUN chown -R appuser:appuser /app
USER appuser

# Expose flask/gunicorn port
EXPOSE 5001

# Run the Flask app with gunicorn (production)
CMD ["gunicorn", "-b", "0.0.0.0:5001", "app.application:app"]