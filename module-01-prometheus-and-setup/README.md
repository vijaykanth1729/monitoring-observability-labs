# Module 1: Prometheus and setup

In this lab you build a small monitoring setup, one piece at a time.

By the end you will have three things running with Docker Compose, and you will see all three on the Prometheus **Targets** page:

| Piece | What it is | Port |
|-------|------------|------|
| Sample app | A tiny web app. It shows its own numbers (metrics). It can also make errors on purpose. | 8000 |
| Node Exporter | A helper that shows metrics about the machine: CPU, memory, disk | 9100 |
| Prometheus | Collects metrics from the other two and stores them | 9090 |

## The plan

| Step | Folder | What you do |
|------|--------|-------------|
| 1 | `step-1-sample-app` | Run the sample app alone and read its metrics |
| 2 | `step-2-node-exporter` | Run Node Exporter alone and read its metrics |
| 3 | `step-3-prometheus` | Run Prometheus alone. It watches only itself |
| 4 | `step-4-all-together` | Put all three in one file. Prometheus watches everything |
| 5 | same folder as step 4 | Stop one app and watch Prometheus notice |

**Rule for every step:** when you finish, run `docker compose down` before you go to the next step.

Open a terminal in this folder (`module-01-prometheus-and-setup`) before you start.

---

## Step 1: Run the sample app

### The file

`step-1-sample-app/docker-compose.yml`

```yaml
services:
  sample-app:
    build: ../sample-app
    ports:
      - "8000:8000"
```

### What each line means

| Line | Meaning |
|------|---------|
| `services:` | The list of programs we want to run. Each program is called a **service**. |
| `sample-app:` | The name we give to this service. We choose it. Later, other services use this name to find it. |
| `build: ../sample-app` | Docker builds the app from the folder `sample-app` (it has a `Dockerfile`). |
| `ports: - "8000:8000"` | Opens a door from your laptop to the container. Left number = your laptop. Right number = inside the container. |

A **container** is one running program, packed with everything it needs.

### Run it

```bash
cd step-1-sample-app
docker compose up -d --build
docker compose ps
```

- `up` starts the services in the file.
- `-d` runs them in the background, so your terminal stays free.
- `--build` builds the app first.
- `ps` lists what is running.

You should see one service, `sample-app`, with status `running` and port `8000`.

### Look at it

Open these in your browser:

| Address | What you see |
|---------|--------------|
| http://localhost:8000 | `hello from the sample app` |
| http://localhost:8000/work | `work done` (it waits a short time on purpose) |
| http://localhost:8000/error | `something broke on purpose` (this is an error, HTTP 500) |
| http://localhost:8000/metrics | The app's metrics, as plain text |

Visit `/work` a few times and `/error` twice. Then open `/metrics` again.

### How to read /metrics

Look for lines like these:

```
app_http_requests_total{method="GET",path="/work",status="200"} 5
app_http_requests_total{method="GET",path="/error",status="500"} 2
```

- `app_http_requests_total` is the **metric name**. It counts requests.
- The part in `{ }` is the **labels**. They say which requests: path `/work`, status `200`.
- The number at the end is the **value**: how many so far.

Prometheus will read this page again and again. That is how it collects metrics.

### Logs

The app also writes a log line for every request:

```bash
docker compose logs sample-app
```

We use these logs later in the course.

### Stop it

```bash
docker compose down
cd ..
```

---

## Step 2: Run Node Exporter

### The file

`step-2-node-exporter/docker-compose.yml`

```yaml
services:
  node-exporter:
    image: prom/node-exporter:v1.9.1
    ports:
      - "9100:9100"
```

### What is new

| Line | Meaning |
|------|---------|
| `image: prom/node-exporter:v1.9.1` | In step 1 we built our own app. Here we use a ready-made **image** from the internet. The part after `:` is the version. |

An **image** is a ready package. A container is an image that is running.

Node Exporter shows metrics about the machine it runs on. On Windows and Mac this is the small Linux machine that Docker Desktop runs inside. That is fine for learning.

### Run it

```bash
cd step-2-node-exporter
docker compose up -d
docker compose ps
```

The first time, Docker downloads the image. This can take a minute.

### Look at it

Open http://localhost:9100/metrics

It is a long page. Press `Ctrl+F` and search for `node_cpu` or `node_memory`. Same format as step 1: a name, labels, a value.

### Stop it

```bash
docker compose down
cd ..
```

---

## Step 3: Run Prometheus

### The files

`step-3-prometheus/docker-compose.yml`

```yaml
services:
  prometheus:
    image: prom/prometheus:v3.5.0
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

`step-3-prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["localhost:9090"]
```

### What is new

| Line | Meaning |
|------|---------|
| `volumes:` | Shares a file or folder from your laptop with the container. |
| `./prometheus.yml:/etc/prometheus/prometheus.yml` | Our file on the left appears at the path on the right, inside the container. Prometheus reads its settings from that path. |

Inside `prometheus.yml`:

| Line | Meaning |
|------|---------|
| `scrape_interval: 15s` | Prometheus visits each target every 15 seconds. |
| `scrape_configs:` | The list of things to scrape. |
| `job_name: prometheus` | A name for this group of targets. It becomes a label later. |
| `targets: ["localhost:9090"]` | The address to scrape. Here Prometheus scrapes **itself**. Inside a container, `localhost` means the container itself. |

### Run it

```bash
cd step-3-prometheus
docker compose up -d
docker compose ps
```

### Look at it

1. Open http://localhost:9090. This is the Prometheus web page.
2. Go to **Status**, then **Targets** (the menu name can differ a little between versions), or open http://localhost:9090/targets
3. You see one target, `prometheus`, with state **UP**.
4. Go to the **Query** page (or **Graph** in older versions). Type `up` and click **Execute**.

You get one row with value `1`. The metric `up` is made by Prometheus for every target: `1` means the last scrape worked, `0` means it failed.

Prometheus only watches itself right now. Next we add the other two.

### Stop it

```bash
docker compose down
cd ..
```

---

## Step 4: Put it all together

Now we join the three services in one file. Open `step-4-all-together/docker-compose.yml`:

```yaml
services:
  sample-app:
    build: ../sample-app
    ports:
      - "8000:8000"

  node-exporter:
    image: prom/node-exporter:v1.9.1
    ports:
      - "9100:9100"

  prometheus:
    image: prom/prometheus:v3.5.0
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

Nothing new here. It is step 1, 2 and 3 side by side under one `services:`.

### One important idea: service names

When Docker Compose starts these services, it puts them on the same private network. Each service can reach the others **by its service name**. So Prometheus can use `sample-app` and `node-exporter` as addresses.

Open `step-4-all-together/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: node-exporter
    static_configs:
      - targets: ["node-exporter:9100"]

  - job_name: sample-app
    static_configs:
      - targets: ["sample-app:8000"]
```

We added two jobs. Look at the targets: `node-exporter:9100` and `sample-app:8000`. These are the service names from the compose file, plus the port **inside** the container.

### Run it

```bash
cd step-4-all-together
docker compose up -d --build
docker compose ps
```

You should see three services running.

### Look at it

1. Open http://localhost:9090/targets and wait up to 30 seconds. You see three targets, all **UP**.
2. Open http://localhost:8000/work and http://localhost:8000/error a few times.
3. In the Prometheus **Query** page, run `up`. You get three rows, each with value `1`.
4. Click on a row. Look at its labels: `job` and `instance`.
5. Run `app_http_requests_total`. These are the numbers from step 1, now collected by Prometheus.

---

## Step 5: Break it and fix it

Keep the step 4 stack running.

1. Stop the sample app:

   ```bash
   docker compose stop sample-app
   ```

2. Wait about 20 seconds. Refresh http://localhost:9090/targets. The `sample-app` target is **DOWN**. The other two stay UP. Look at the error message in that row.

3. Start it again:

   ```bash
   docker compose start sample-app
   ```

4. Wait about 20 seconds and refresh. It is **UP** again.

### If a target is DOWN, check in this order

1. Is the container running? (`docker compose ps`)
2. Is the address and port correct in `prometheus.yml`?
3. Does the target's own page open in the browser? (for example http://localhost:8000/metrics)

---

## Commands you used

| Command | What it does |
|---------|--------------|
| `docker compose up -d` | Start the services in the background |
| `docker compose up -d --build` | Build our app first, then start |
| `docker compose ps` | Show running services |
| `docker compose logs <service>` | Show the logs of one service |
| `docker compose stop <service>` | Stop one service |
| `docker compose start <service>` | Start it again |
| `docker compose down` | Stop and remove everything in this file |

## Words you learned

| Word | Meaning |
|------|---------|
| Service | One program in a compose file |
| Image | A ready package of a program |
| Container | An image that is running |
| Port mapping | `laptop:container`, the door into a container |
| Volume | A file or folder shared into a container |
| Target | Something Prometheus scrapes |
| Scrape | One visit by Prometheus to read a target's metrics |
| Metric, label, value | The name, the details, and the number on one line of `/metrics` |
| `up` | A metric: `1` means the last scrape worked, `0` means it failed |

## Finish

When you are done, run `docker compose down` in the step 4 folder.

Next module: asking Prometheus questions with PromQL. It starts from the step 4 stack.
