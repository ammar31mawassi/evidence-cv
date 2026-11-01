FROM python:3.12.13-slim-bookworm
ENV PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
RUN apt-get update && apt-get install -y --no-install-recommends texlive-latex-base texlive-latex-extra texlive-fonts-recommended poppler-utils && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && python -m playwright install --with-deps chromium
ARG INSTALL_CRAWL4AI=0
RUN if [ "$INSTALL_CRAWL4AI" = "1" ]; then pip install crawl4ai==0.9.5 && python -m playwright install --with-deps chromium; fi
RUN if [ "$INSTALL_CRAWL4AI" = "1" ]; then pip install chardet==5.2.0; fi
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8012"]
