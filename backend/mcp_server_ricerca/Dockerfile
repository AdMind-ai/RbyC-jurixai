FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-por tesseract-ocr-eng tesseract-ocr-ita \
        antiword unrtf poppler-utils \
        flac ffmpeg lame libmad0 libsox-fmt-mp3 sox \
        libjpeg-dev swig libxml2-dev libxslt1-dev python3-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "server/server.py"]