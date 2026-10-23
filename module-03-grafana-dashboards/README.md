# Module 3: Grafana dashboards

In module 2 we asked Prometheus questions by typing queries. That works, but nobody wants to type queries all day.

**Grafana** turns those queries into a **dashboard**: a page of panels that shows the health of your system at a glance.

By the end of this lab you build a dashboard with three panels:

| Panel | Question it answers | Type |
|-------|---------------------|------|
| App status | Is the sample app up? | Stat |
| Requests per second | How busy is it, and how does it change? | Time series |
| Error percentage | What share of requests fail? | Stat |

## Before you start

- Docker is running (see the main README).
- You have the whole repository on your laptop. This lab reuses the sample app from `module-01-prometheus-and-setup`.
- Ports 3000, 8000, 9090 and 9100 must be free. If the module 2 stack is still running, stop it first: open a terminal in `module-02-beginner-promql` and run `docker compose down`. Not sure? `docker ps` shows what is running.

Open a terminal in this folder (`module-03-grafana-dashboards`).

## The plan

| Step | What you do |
|------|-------------|
| 0 | Start the stack. It is the module 2 stack plus Grafana |
| 1 | Open Grafana and look around |
| 2 | Connect Grafana to Prometheus (add a data source) |
| 3 | Check the connection in Explore |
| 4 | Panel 1: is the app up? |
| 5 | Panel 2: requests per second |
| 6 | Panel 3: error percentage |
| 7 | Make the dashboard easy to read and save it |
| 8 | Break something and watch the dashboard |

---

## Step 0: Start the stack

### The file

`docker-compose.yml` has the four services from module 2 (sample app, Node Exporter, Prometheus, traffic) and one new service: `grafana`.

```yaml
  grafana:
    image: grafana/grafana:12.0.2
    depends_on:
      - prometheus
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  grafana-data:
```

### What is new

| Line | Meaning |
|------|---------|
| `image: grafana/grafana:12.0.2` | The ready-made Grafana image, with a fixed version. |
| `depends_on: - prometheus` | Start Prometheus first. |
| `"3000:3000"` | Grafana's web page is on port 3000. |
| `environment:` | Settings we give to the container. Here: the login name and password. |
| `GF_SECURITY_ADMIN_USER: admin` and `GF_SECURITY_ADMIN_PASSWORD: admin` | Login is `admin` / `admin`. This is fine for a lab on your laptop. **Never** use it in a real system. |
| `grafana-data:/var/lib/grafana` | A **named volume**. Grafana saves its data (our dashboards) in a place that Docker keeps even when the container is removed. |

In module 1 a volume shared a **file** from your laptop. A named volume is different: Docker owns it, and it is only for saving data. Without it, our dashboard would disappear after `docker compose down`.

### Run it

```bash
docker compose up -d --build
docker compose ps
```

You should see five services running: sample-app, node-exporter, prometheus, grafana and traffic.

Open http://localhost:9090/targets and check that all three targets are **UP**.

---

## Step 1: Open Grafana

Open http://localhost:3000

1. Login: `admin` and `admin`.
2. Grafana asks you to set a new password. Click **Skip**.

Look at the left menu. These are the parts we use today:

| Menu item | What it is |
|-----------|-----------|
| **Connections** (Data sources) | Where we tell Grafana where the data lives |
| **Explore** | A free place to try a query, like the Query page in Prometheus |
| **Dashboards** | Where our saved dashboards live |

Right now Grafana is empty. It does not know about Prometheus yet.

---

## Step 2: Add Prometheus as a data source

A **data source** is a connection to a place where data lives. Grafana does not store metrics. It asks a data source.

1. Open the menu, then **Connections**, then **Data sources**.
2. Click **Add data source**.
3. Choose **Prometheus**.
4. In **Connection**, set **Prometheus server URL** to:

```
http://prometheus:9090
```

5. Leave everything else as it is. Scroll down and click **Save & test**.
6. You should see a green message: *Successfully queried the Prometheus API*.

### Why `prometheus:9090` and not `localhost:9090`?

Grafana runs inside its own container. For that container, `localhost` means **itself**, not your laptop and not Prometheus. Inside Docker Compose, services find each other by **service name**. The service is called `prometheus`, so the address is `http://prometheus:9090`. This is the same idea as module 1, where Prometheus used `sample-app:8000`.

---

## Step 3: Check it in Explore

1. Open **Explore** in the left menu.
2. Make sure the data source at the top is **prometheus**.
3. Switch the query editor to **Code** (a button near the query box).
4. Type `up` and press **Shift + Enter** (or click **Run query**).

You see the same three targets as in module 2. Grafana is now asking Prometheus the same questions.

---

## Step 4: Panel 1, is the app up?

### Create the dashboard and panel

1. Open **Dashboards**, then **New**, then **New dashboard**.
2. Click **Add visualization**.
3. Choose the **prometheus** data source.

You see three areas: the preview on top, the **query** at the bottom, and the **options** on the right.

### The query

In the query editor, switch to **Code** and type:

```
up{job="sample-app"}
```

### The visualization

At the top right, choose the type **Stat**. A Stat panel shows one big number.

You see `1`. A number is not friendly, so let us make it say UP or DOWN.

### Make it readable

In the options on the right (use the search box at the top of the options to find each one):

| Option | Set it to |
|--------|-----------|
| **Title** | `App status` |
| **Value mappings** | Add mapping. Value `1` becomes text `UP`, colour green. Value `0` becomes text `DOWN`, colour red |
| **Color mode** | Background |

The panel is now a big green box that says **UP**.

Click **Back to dashboard** (top right).

---

## Step 5: Panel 2, requests per second

1. Click **Add**, then **Visualization**.
2. Choose the **prometheus** data source.
3. Query (in Code mode):

```
sum by (path) (rate(app_http_requests_total[1m]))
```

This is from module 2: requests per second, one line for each path.

4. The visualization type is **Time series** (a line chart over time). That is the default.

### Make it readable

| Option | Set it to |
|--------|-----------|
| **Title** | `Requests per second` |
| **Legend**, query option **Legend** (below the query box) | Custom, and type `{{path}}` |
| **Standard options**, **Unit** | Throughput, then `requests/sec (rps)` |

### Why the legend?

Without a legend, each line is named with a long label text like `{path="/work"}`. `{{path}}` tells Grafana: use only the value of the `path` label. Now the lines are called `/`, `/work` and `/error`.

Click **Back to dashboard**.

---

## Step 6: Panel 3, error percentage

1. **Add**, then **Visualization**, data source **prometheus**.
2. Query:

```
sum(rate(app_http_requests_total{status="500"}[1m]))
/
sum(rate(app_http_requests_total[1m]))
```

This is the health check from module 2: errors divided by total.

3. Choose the type **Stat**.

### Make it readable

| Option | Set it to |
|--------|-----------|
| **Title** | `Error percentage` |
| **Standard options**, **Unit** | Misc, then `Percent (0.0-1.0)` |
| **Thresholds** | Keep green as the base. Add a threshold at `0.2` and make it red |
| **Color mode** | Background |

### What are thresholds?

A threshold is a line. Below it the panel is green. Above it (here, above 20%) the panel turns red. Our app fails about 9% of the time, so the panel stays green.

Click **Back to dashboard**.

---

## Step 7: Make the dashboard easy to read, and save it

### Layout

Drag the panels so that the two stat panels are at the top, side by side, and the chart is below, wide. Drag the bottom-right corner of a panel to resize it.

### Time range and refresh

At the top right of the dashboard:

| Setting | Set it to | Why |
|---------|-----------|-----|
| **Time range** | `Last 15 minutes` | How far back the charts look |
| **Auto refresh** (the refresh icon with a drop-down) | `10s` | The dashboard updates itself |

### Save

1. Click **Save dashboard** (the disk icon).
2. Title: `Sample App Health`.
3. Click **Save**.

Dashboards are just a JSON file. Later, a team can keep them in Git.

---

## Step 8: Break it and watch

Stop the sample app:

```bash
docker compose stop sample-app
```

Wait about 30 seconds and look at your dashboard (it refreshes by itself):

- **App status** turns red and says **DOWN**.
- **Requests per second** drops to nothing.
- **Error percentage** shows **No data**. This is correct: with no requests there is nothing to divide.

Start it again:

```bash
docker compose start sample-app
```

After about a minute everything comes back. In the chart you can see the gap in time. This is why we monitor: the dashboard shows what happened, and when.

---

## Clean up

```bash
docker compose down
```

Your dashboard is saved in the `grafana-data` volume, so it is still there next time. To remove it too, run `docker compose down -v`.

## Commands you used

| Command | What it does |
|---------|--------------|
| `docker compose up -d --build` | Start everything |
| `docker compose stop <service>` | Stop one service |
| `docker compose start <service>` | Start it again |
| `docker compose down` | Stop and remove the containers (the volume stays) |
| `docker compose down -v` | Also remove the volumes |

## Words to remember

| Word | Meaning |
|------|---------|
| Data source | A connection from Grafana to where data lives |
| Dashboard | A page of panels |
| Panel | One chart or number. It has a query and a visualization |
| Visualization | How a panel draws the result: Stat, Time series, and so on |
| Legend | The names of the lines in a chart |
| Unit | What the number means: percent, requests per second |
| Threshold | A value where the colour changes |
| Named volume | Storage kept by Docker, so data survives `down` |

## Common problems

| You see | What to do |
|---------|-----------|
| Data source test fails | The URL must be `http://prometheus:9090`, not `localhost`. Check `docker compose ps` |
| Panel says `No data` | Wait two minutes after start. Check the query spelling. Check the time range at the top right |
| Port 3000 is already allocated | Something else uses port 3000. Stop it, or change the left number in `"3000:3000"` |
| Cannot log in | Login is `admin` and `admin`. If you changed the password before, run `docker compose down -v` to start fresh |
| `rate()` panel is empty | Prometheus needs a few scrapes. Wait one or two minutes |
