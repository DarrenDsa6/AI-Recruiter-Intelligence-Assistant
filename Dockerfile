FROM node:20-slim AS frontend-build
WORKDIR /app
ARG REACT_APP_API_URL=
ENV REACT_APP_API_URL=$REACT_APP_API_URL
COPY frontend/recruiter-ui/package.json frontend/recruiter-ui/package-lock.json* ./
RUN npm install
COPY frontend/recruiter-ui/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends g++ && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend-build /app/build ./static

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
