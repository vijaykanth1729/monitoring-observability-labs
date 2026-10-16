# Monitoring & Observability with Prometheus, Grafana and Loki: Labs

Hands-on labs for the course. Every lab runs on your own laptop with Docker. No cloud account needed.

## Modules

| Module | Topic | Folder |
|--------|-------|--------|
| 1 | Prometheus and setup | [`module-01-prometheus-and-setup`](module-01-prometheus-and-setup/) |

More modules are added as the course continues.

## What you need

- A laptop with 8 GB RAM or more
- **Docker Desktop** (Windows or Mac) or **Docker Engine with the Compose plugin** (Linux)
- A web browser
- A code editor. [VS Code](https://code.visualstudio.com/) is a good choice.
- Git (optional, you can also download the repository as a ZIP file)

## Check Docker works

Open a terminal (PowerShell on Windows) and run:

```bash
docker --version
docker compose version
```

Both commands should print a version. If you see an error, start Docker Desktop and wait one minute, then try again.

## Get the labs

```bash
git clone <this-repository-url>
cd monitoring-observability-labs
```

No Git? Click **Code**, then **Download ZIP**, and unzip it.

## How the labs work

- Each module has its own folder with its own README. Open it and follow the steps in order.
- Work in small steps. Each step has its own folder and its own `docker-compose.yml`.
- When you finish a step, run `docker compose down` before you start the next one.
- Commands are the same on Windows, Mac and Linux, unless the README says otherwise.

## Common problems

| You see | What it means | What to do |
|---------|---------------|------------|
| `Cannot connect to the Docker daemon` | Docker is not running | Start Docker Desktop, wait one minute, try again |
| `port is already allocated` | Another program uses that port | Run `docker compose down` in the other step folder. Still stuck? Change the **left** number in `ports`, for example `"8001:8000"`, and open that port in the browser |
| A page does not open | The container may have stopped | Run `docker compose ps`, then `docker compose logs` |
| Image pull is slow or fails | Network problem | Check your internet and run the command again |

## Start fresh

To stop everything from a step folder:

```bash
docker compose down
```
