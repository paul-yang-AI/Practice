FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY requirements-docker.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY . .

ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

EXPOSE 8501

HEALTHCHECK CMD python task1_agent/smoke_playwright.py || exit 1

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
