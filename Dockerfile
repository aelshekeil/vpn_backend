# Dockerfile for Flask Backend (vpn_backend)

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variables (can be overridden by Coolify)
ENV FLASK_APP=src/main.py
ENV FLASK_RUN_HOST=0.0.0.0
# Ensure DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME, STRIPE_SECRET_KEY, STRIPE_PRICE_ID, STRIPE_WEBHOOK_SECRET, FRONTEND_URL are set in Coolify

# Command to run the application using Gunicorn (recommended for production)
# Coolify might override this with its own start command, but it's good practice to have one.
# Ensure gunicorn is in requirements.txt if you use this directly.
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "src.main:app"]
# For development/simplicity, or if Coolify handles the WSGI server:
CMD ["python", "src/main.py"]

