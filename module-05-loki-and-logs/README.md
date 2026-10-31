# Module 5: Loki and logs

Metrics tell us **that** something is wrong. For example: 9% of requests fail.

Logs tell us **why**. For example: `database connection refused`.

In this lab you add **Loki** (it stores logs) and **Alloy** (it collects logs), and then you read the logs of the sample app inside Grafana.

## Before you start

- Docker is running (see the main README).
- You have the whole repository on your laptop. This lab reuses the sample app from `module-01-prometheus-and-setup`.
- Ports 3000, 3100, 8000, 9090, 9093, 9100 and 12345 must be free. If the module 4 stack is still running, stop it first: open a terminal in `module-04-simple-alerting` and run `docker compose down`. Not sure? `docker ps` shows what is running.

Open a terminal in this folder (`module-05-loki-and-logs`).

## The plan

| Step | What you do |
|------|-------------|
| 0 | Start the stack. It is the module 4 stack plus Loki and Alloy |
| 1 | Understand the two new configs |
| 2 | Check that Loki and Alloy are running |
| 3 | Add Loki as a data source in Grafana |
| 4 | Read logs in Explore and write four LogQL queries |
| 5 | Add a Logs panel to the dashboard |
| 6 | Create an error and find it in the logs |

## The path of a log line

```
sample-app  -->  container output  -->  Alloy  -->  Loki  -->  Grafana
 (writes)         (Docker keeps it)    (collects)  (stores)    (shows)
```

The sample app only prints a line for every request. Docker keeps what a container prints. Alloy reads it and pushes it to Loki. Grafana asks Loki, like it asks Prometheus for metrics.

---

## Step 0: Start the stack

### What is new

| New thing | What it is |
|-----------|-----------|
| `loki` service | Stores logs. Port 3100 |
| `alloy` service | Collects logs and sends them to Loki. Port 12345 shows its web page |
| `loki.yml` | The settings of Loki |
| `config.alloy` | The settings of Alloy |

In `docker-compose.yml`:

```yaml
  loki:
    image: grafana/loki:3.5.0
    ports:
      - "3100:3100"
    command:
      - -config.file=/etc/loki/loki.yml
    volumes:
      - ./loki.yml:/etc/loki/loki.yml

  alloy:
    image: grafana/alloy:v1.9.0
    depends_on:
      - loki
    ports:
      - "12345:12345"
    command:
      - run
      - --server.http.listen-addr=0.0.0.0:12345
      - --storage.path=/var/lib/alloy/data
      - /etc/alloy/config.alloy
    volumes:
      - ./config.alloy:/etc/alloy/config.alloy
      - /var/run/docker.sock:/var/run/docker.sock
```

| Line | Meaning |
|------|---------|
| `command:` | The command and options the container starts with. Both programs need to be told where their config file is. |
| `./loki.yml:/etc/loki/loki.yml` | A file from your laptop, shown inside the container. Same idea as Prometheus in module 1. |
| `/var/run/docker.sock:/var/run/docker.sock` | The Docker socket. This is how Alloy asks Docker: which containers are running, and what do they print? Alloy only reads. |

### Run it

```bash
docker compose up -d --build
docker compose ps
```

You should see eight services running: sample-app, node-exporter, prometheus, alertmanager, grafana, traffic, loki and alloy. Loki needs about 15 seconds before it is ready.

---

## Step 1: Understand the two configs

### `loki.yml` (Loki settings)

This is a small, single-copy Loki that saves its data on its own disk. You do not need to know every line. These are the important ones:

| Line | Meaning |
|------|---------|
| `auth_enabled: false` | No login needed. Fine for a lab. |
| `http_listen_port: 3100` | The port where Loki listens. |
| `storage: filesystem` | Logs are saved in files inside the container. Simple. (Real systems use object storage like S3.) |
| `schema: v13` and `store: tsdb` | How Loki arranges its index. Use these values as they are. |

### `config.alloy` (Alloy settings)

Alloy is built from small steps. Each step is called a **component**, and one step feeds the next:

```alloy
discovery.docker "containers" { ... }        // 1. find running containers
discovery.relabel "containers" { ... }       // 2. add labels: service, container
loki.source.docker "containers" { ... }      // 3. read their logs
loki.write "local" { ... }                   // 4. send to Loki
```

| Step | Meaning |
|------|---------|
| `discovery.docker` | Asks Docker for the list of running containers. |
| `discovery.relabel` | Makes labels. We take the Docker Compose service name (`sample-app`, `prometheus`...) and call it `service`. |
| `loki.source.docker` | Reads the logs of every container found. `forward_to` says where to pass them. |
| `loki.write` | Pushes the logs to Loki at `http://loki:3100`. A service name again. |

### Why labels matter

Loki **indexes only the labels**, not the text of the log lines. Labels like `service="sample-app"` are used to find the right logs fast. The text is searched later, when you query. This is why Loki is small and cheap.

---

## Step 2: Check that Loki and Alloy are running

Open http://localhost:3100/ready. It says `ready`. (If it says `Ingester not ready`, wait 15 seconds and refresh.)

Open http://localhost:12345. This is the Alloy page. Click **Graph** to see the four components connected, in the same order as the config file.

---

## Step 3: Add Loki as a data source in Grafana

1. Open http://localhost:3000 (login: `admin` and `admin`).
2. **Connections**, then **Data sources**, then **Add data source**.
3. Choose **Loki**.
4. **URL** (Connection):

```
http://loki:3100
```

5. Scroll down and click **Save & test**. You should see a green message: *Data source successfully connected*.

Just like Prometheus in module 3: we use the **service name**, not `localhost`.

---

## Step 4: Read logs in Explore

1. Open **Explore**.
2. Choose the data source **loki** (top left).
3. Switch the query editor to **Code**.

### Query 1: a stream selector

```
{service="sample-app"}
```

Everything inside `{ }` is a **label filter**, like in PromQL. This selects all log lines of the sample app. Make sure the time range (top right) is `Last 15 minutes`.

You see lines like:

```
ts=2026-10-31T10:00:00 level=info msg="request handled" method=GET path=/work status=200 duration_ms=153
```

### Query 2: a text filter

```
{service="sample-app"} |= "error"
```

`|=` means: the line **contains** this text. Now you see only the error lines:

```
ts=... level=error msg="database connection refused" method=GET path=/error status=500 duration_ms=0
```

This is the answer to "why": `database connection refused`.

### Query 3: exclude text

```
{service="sample-app"} != "/work"
```

`!=` means: the line does **not** contain this text. Other filters:

| Operator | Meaning |
|----------|---------|
| `\|=` | contains |
| `!=` | does not contain |
| `\|~` | matches a pattern |
| `!~` | does not match a pattern |

### Query 4: from logs to numbers

```
sum(count_over_time({service="sample-app"} |= "error" [1m]))
```

`count_over_time(... [1m])` counts the log lines in the last minute. You get a number, so Grafana can draw a chart. It looks like the PromQL `rate()` you know: a window in square brackets.

The result is about 10 errors per minute.

### Other services

Change the label value: `{service="prometheus"}`, `{service="grafana"}` or `{service="alloy"}`. Every container of the stack sends its logs.

---

## Step 5: Add a Logs panel to the dashboard

If you did module 3 on this laptop, your dashboard **Sample App Health** is still there.

1. **Dashboards**, open **Sample App Health**.
2. **Add**, then **Visualization**. Choose the data source **loki**.
3. Query (Code mode):

```
{service="sample-app"}
```

4. At the top right, choose the visualization **Logs**.
5. **Title:** `Sample app logs`.
6. **Back to dashboard**. Drag the logs panel to the bottom, wide.
7. **Save dashboard**.

Now metrics and logs are on the same page. If you did not do module 3, create a new dashboard instead, and add the panel there.

---

## Step 6: Create an error and find it in the logs

1. Open http://localhost:8000/error in your browser a few times.
2. In Grafana, look at the Logs panel (or run `{service="sample-app"} |= "error"` in Explore).
3. You see new error lines at the top, with the time they happened.

This is how logs help: the metric says "errors went up". The log says "database connection refused", on this path, at this exact time.

---

## Clean up

```bash
docker compose down
```

Loki saves its logs inside the container, so they are removed with it. The Grafana volume stays.

## Commands you used

| Command | What it does |
|---------|--------------|
| `docker compose up -d --build` | Start everything |
| `docker compose ps` | Show running services |
| `docker compose logs <service>` | Show the logs of a service in the terminal |
| `docker compose down` | Stop and remove the containers |

## Words to remember

| Word | Meaning |
|------|---------|
| Log | A text line an application writes about what happened |
| Loki | The database for logs. It indexes labels, not text |
| Alloy | The collector. It reads logs and sends them to Loki |
| Label | A key and value on a log stream, like `service="sample-app"` |
| Stream | All log lines that have the same labels |
| LogQL | The query language of Loki. Selectors in `{ }`, then filters |
| Line filter | `\|=`, `!=`, `\|~`, `!~` after the selector |
| `count_over_time` | Counts log lines in a time window |

## Common problems

| You see | What to do |
|---------|-----------|
| Data source test fails | URL must be `http://loki:3100`, not `localhost`. Check `docker compose ps` |
| `{service="sample-app"}` returns nothing | Wait one minute. Set the time range to `Last 15 minutes`. Check Alloy: `docker compose logs alloy` |
| Alloy cannot read Docker | Check the `docker.sock` line in `docker-compose.yml`. On Linux, you may need to run with permission to the Docker socket |
| `Ingester not ready` | Loki is still starting. Wait 15 seconds |
| `port is already allocated` | Run `docker compose down` in the module 4 folder |
| Old logs are gone | Loki's logs are removed when you run `docker compose down` |
