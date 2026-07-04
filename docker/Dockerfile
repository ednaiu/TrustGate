FROM python:3.12-slim
RUN pip install --no-cache-dir "pytest==8.*"
RUN useradd -m runner
USER runner
WORKDIR /work
