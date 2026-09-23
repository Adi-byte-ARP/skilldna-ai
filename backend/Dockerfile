# Bakes Tesseract OCR into the image so OCR works out of the box on any
# machine that can run this container -- no manual "install tesseract"
# step for whoever deploys or runs this, on any OS.
FROM python:3.12-slim

# tesseract-ocr: the actual OCR engine (this is the whole point of this file)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# TESSERACT_CMD is intentionally left unset here -- apt installs tesseract
# to /usr/bin/tesseract, which is already on PATH inside this image, so
# pytesseract finds it automatically. (TESSERACT_CMD only matters for local
# Windows dev, where PATH often isn't set up by the installer.)
ENV DATABASE_URL=sqlite:////app/data/skilldna.db
RUN mkdir -p /app/data /app/uploads

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
