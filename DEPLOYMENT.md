# Deployment guide

The project deploys as two services:

- **Backend:** FastAPI on Render.
- **Frontend:** React/Vite static build on Vercel.

The local Docker URL and the public deployment URL are intentionally
different. `http://localhost:8000` only works on the computer running Docker.
The deployed frontend must use the public backend URL.

## 1. Deploy the backend to Render

1. Create a new Render Web Service from the repository.
2. Use the included `render.yaml`, or configure these values manually:

```text
Root directory: backend
Runtime: Python
Build command: pip install -r requirements.txt
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health check path: /api/health
```

3. After the service is deployed, copy its public URL, for example:

```text
https://wind-forecast-analytics-api.onrender.com
```

4. Verify the backend:

```text
https://YOUR-BACKEND-URL/api/health
```

The response must be:

```json
{"status":"ok"}
```

## 2. Configure backend CORS

In the Render service environment variables, set:

```text
WIND_CORS_ORIGINS=https://YOUR-FRONTEND-URL.vercel.app
```

Multiple origins can be separated by commas:

```text
WIND_CORS_ORIGINS=https://example.vercel.app,https://custom-domain.example
```

Do not use `*` for the deployed application unless there is a specific
reason to allow every origin.

## 3. Deploy the frontend to Vercel

1. Import the repository into Vercel.
2. Set the project root directory to `frontend`.
3. Vercel can use the included `frontend/vercel.json`.
4. Add this environment variable before deploying:

```text
VITE_API_BASE_URL=https://YOUR-BACKEND-URL.onrender.com
```

5. Deploy the frontend.
6. Copy the generated Vercel URL and update the Render
   `WIND_CORS_ORIGINS` value with that exact origin.
7. Redeploy the backend after changing CORS.

`VITE_API_BASE_URL` is embedded into the frontend at build time. Changing the
Vercel environment variable requires a new frontend deployment.

## 4. Verify the public deployment

Check these URLs in an incognito browser:

```text
https://YOUR-BACKEND-URL/api/health
https://YOUR-FRONTEND-URL.vercel.app
```

Then verify:

- The dashboard loads without a CORS error.
- January 2026 analytics data appears.
- Changing the date range makes a new request.
- The backend health check is successful.
- The browser developer console has no failed API requests.

## Local versus public URLs

| Environment | Frontend API URL |
|---|---|
| Local Vite | `http://localhost:8000` |
| Local Docker | `http://localhost:8000` |
| Vercel deployment | `https://YOUR-BACKEND-URL.onrender.com` |

This is not a bug. A browser cannot resolve the private Compose service name
`backend`, and a deployed browser cannot reach your local machine's
`localhost`.

## Hosting limitations

- Render free services may sleep when idle and have cold-start delays.
- Elexon requests happen when the dashboard requests analytics, so a cold
  backend can make the first dashboard load slower.
- Provider deployment cannot be verified locally until the service URLs and
  hosting accounts exist.
