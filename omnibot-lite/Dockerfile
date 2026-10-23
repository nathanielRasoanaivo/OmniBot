# omnibot-lite — image unique : build du frontend Vite puis FastAPI sert API + SPA.

# --- Étape 1 : frontend ---
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Étape 2 : backend + statiques ---
FROM python:3.12-slim
WORKDIR /srv/app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /srv/app/
COPY --from=web /web/dist /srv/static

ENV OMNIBOT_STATIC_DIR=/srv/static
ENV OMNIBOT_DATA_DIR=/data
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
