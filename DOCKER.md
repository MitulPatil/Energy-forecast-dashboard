# Running Wind Forecast Analytics with Docker

Docker packages an application and its dependencies into an **image**. A
running copy of an image is a **container**. Docker Compose starts the
backend and frontend containers together using `docker-compose.yml`.

## Prerequisites

Install Docker Desktop and make sure it is running. Verify it with:

```powershell
docker --version
docker compose version
```

## Start the application

From the project root:

```powershell
docker compose up --build
```

What happens:

1. Docker builds the Python backend image from `backend/Dockerfile`.
2. Docker builds the React application in a temporary Node image.
3. The compiled React files are copied into a small Nginx image.
4. Compose starts the backend on port `8000`.
5. Compose waits for the backend health check.
6. Compose starts the frontend on port `8080`.

Open the dashboard at <http://localhost:8080>.

The browser calls the backend at <http://localhost:8000>. The
`VITE_API_BASE_URL` build argument controls this browser-facing URL; it must
be a URL that the browser can reach, not the Compose service name.

## Useful commands

Run in the background:

```powershell
docker compose up --build -d
```

Show service status and health:

```powershell
docker compose ps
```

Follow logs:

```powershell
docker compose logs -f backend
docker compose logs -f frontend
```

Stop and remove the containers:

```powershell
docker compose down
```

Rebuild after a Dockerfile or dependency change:

```powershell
docker compose build --no-cache
docker compose up
```

## Ports and networking

The port mapping uses `host:container` syntax:

```text
8000:8000  backend API
8080:80    frontend Nginx
```

Inside the Compose network, the backend is reachable by the service name
`backend`. However, the React code runs in the user's browser, so its API URL
must use `localhost:8000` during local development. This is why the Compose
file uses `backend` for health ordering but `localhost` for the frontend
build argument.

## Health checks

- Backend: `GET /api/health`
- Frontend: `GET /health`

Health checks let Compose report whether a service is ready, rather than only
whether its process exists.

## Troubleshooting

- If port `8000` or `8080` is already in use, stop the conflicting process or
  change the host side of the mapping in `docker-compose.yml`.
- If the frontend shows an API error, check that the backend is healthy and
  open <http://localhost:8000/api/health>.
- If a build uses stale files, run `docker compose build --no-cache`.
- Inspect the exact failure with `docker compose logs backend` or
  `docker compose logs frontend`.
