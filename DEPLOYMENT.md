# Deployment Guide

## Repository Layout

- Frontend: `market-pulse-14-main` (Vite + React) -> deploy on Vercel
- Backend: `pre-open-scanner-main` (FastAPI) -> deploy on Render

## 1) Push To GitHub

Repository target:

- `https://github.com/insightfusionanalytics/Market-Pulse`

## 2) Backend Deployment (Render - Free)

This repository includes `render.yaml` at root.

### Option A: Blueprint Deploy (recommended)

1. In Render, create a new **Blueprint** from this GitHub repo.
2. Render will read `render.yaml` and create service `market-pulse-backend`.
3. Set secret env vars in Render dashboard:
   - `CLIENT_USERNAME`
   - `CLIENT_PASSWORD`
   - `JWT_SECRET_KEY`
   - `REDIS_HOST`
   - `REDIS_PORT`
   - `REDIS_PASSWORD`
   - `REDIS_DB`
   - `CORS_ORIGINS` (include your Vercel domain)
4. Deploy.

### Option B: Manual Web Service

- Root directory: `pre-open-scanner-main`
- Build command: `pip install -r requirements.txt`
- Start command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
- Runtime: Python 3.11 (`runtime.txt`)

## 3) Frontend Deployment (Vercel - Free)

### Project settings

- Framework preset: `Vite`
- Root directory: `market-pulse-14-main`
- Build command: `npm run build`
- Output directory: `dist`

`vercel.json` is included for SPA routing fallback.

### Required Vercel Environment Variable

- `VITE_API_BASE_URL` = your Render backend URL
  - Example: `https://market-pulse-backend.onrender.com`

## 4) CORS for Production

Backend supports:

- `CORS_ORIGINS` (comma-separated exact origins)
- `CORS_ORIGIN_REGEX` (for preview URLs, default in render.yaml supports `*.vercel.app`)

Recommended `CORS_ORIGINS` example:

- `https://your-vercel-prod-domain.vercel.app,https://scanner.insightfusionanalytics.com`

## 5) Health Checks

- Backend health: `GET /health`
- API root: `GET /`
- Swagger docs: `/docs`

## 6) Frontend API config behavior

Frontend reads:

- `VITE_API_BASE_URL`

If missing, it falls back to local development URL `http://localhost:8000`.
