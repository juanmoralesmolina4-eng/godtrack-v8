FROM python:3.10

WORKDIR /code

# Install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the application
COPY . /code

# Create a writable directory for database persistence (optional but good practice)
RUN mkdir -p /code/data && chmod 777 /code/data

# Hugging Face Spaces expects service on port 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
