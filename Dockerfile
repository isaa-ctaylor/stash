# Stage 1: Build the frontend assets (CSS using TailwindCSS)
FROM node:18-alpine AS frontend-builder

# Set working directory inside the container
WORKDIR /app

# Copy only the necessary files for npm install and build
COPY package.json package-lock.json ./

# Install Node.js dependencies
RUN npm install

# Copy your Tailwind CSS configuration and source files
COPY ./tailwind.config.js ./
COPY ./stash/src/css ./stash/src/css
COPY ./stash/src/js ./stash/src/js
COPY ./stash/templates ./stash/templates

# Build and minify the CSS
RUN npm run build

FROM python:3.12-slim AS runtime

# Set the working directory in the container
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y curl

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to the PATH environment variable
ENV PATH="/root/.local/bin:$PATH"

# Copy the pyproject.toml and poetry.lock files to the working directory
COPY pyproject.toml poetry.lock* /app/

# Install the dependencies
RUN poetry install --no-root

# Set working directory inside the container
WORKDIR /app

# Copy the Python application code
COPY ./stash /app
# COPY ./LICENCE ./LICENCE
COPY ./README.md ./README.md

# Copy the built CSS from the frontend-builder stage
COPY --from=frontend-builder /app/stash/static/dist/css ./static/dist/css

# Copy the js to the static folder
# TODO: Minify js
COPY ./stash/src/js ./static/dist/js

# Copy Python dependencies from the python-builder stage
# COPY --from=poetry /app/venv /app/venv
# COPY --from=python-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
# COPY --from=poetry /usr/local/bin /usr/local/bin

# Expose the application port
EXPOSE 8000

# Command to run the FastAPI application
CMD ["poetry", "run", "fastapi", "run", "__main__.py", "--host", "0.0.0.0", "--port", "8000"]
