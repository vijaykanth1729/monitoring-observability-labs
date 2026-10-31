# Module 6: Put it all together and find the problem

You now have all three tools: **Prometheus** (metrics), **Alertmanager** (alerts) and **Loki** (logs), and **Grafana** shows them.

There is nothing new to install in this module. The stack is the same as in module 5. Now we **use** it, the way you would in a real job: something breaks, and you find out what and why.

## Before you start

- Docker is running (see the main README).
- You have the whole repository on your laptop.
- If the module 5 stack is still running, stop it first: open a terminal in `module-05-loki-and-logs` and run `docker compose down`. Not sure? `docker ps` shows what is running.

Open a terminal in this folder (`module-06-end-to-end`).

## The plan

| Step | What you do |
|------|-------------|
| 0 | Start the stack and check that everything is healthy |
| 1 | The three first checks (our checklist) |
| 2 | Problem 1: a burst of errors. Find **what** and **why** |
| 3 | Problem 2: the app goes down. Watch the alert, then fix it |
| 4 | Clean up |

## The first-checks checklist

When something breaks, do not guess. Ask these questions, **in this order**:

| # | Question | Where to look |
|---|----------|---------------|
| 1 | **Is it up?** | Prometheus: `up` (Status, Targets) |
| 2 | **What changed?** | Grafana dashboard or PromQL: requests, errors, errors divided by total |
| 3 | **Why?** | Loki logs: `{service="..."} \|= "error"` |
| 4 | **Is anyone told?** | Prometheus Alerts page and Alertmanager |

Metrics first, to see **what**. Logs second, to see **why**.

---

## Step 0: Start the stack and check it is healthy

```bash
docker compose up -d --build
docker compose ps
```

You should see eight services running: sample-app, node-exporter, prometheus, alertmanager, grafana, traffic, loki and alloy.

Wait about 30 seconds. Then check these four pages. Everything should be green:

| Page | What you should see |
|------|---------------------|
| http://localhost:9090/targets | Every target is **UP** |
| http://localhost:9090/alerts | Alert `SampleAppDown` is **inactive** (green) |
| http://localhost:3100/ready | The word `ready` |
| http://localhost:3000 | Grafana (login `admin` and `admin`). The dashboard **Sample App Health** is there if you did module 3 |

This is our **normal** state. Remember how it looks. A problem is only visible when you know what normal is.

---

## Step 1: The three first checks

### Check 1: Is it up?

In Prometheus (http://localhost:9090), run:

```
up
```

Every row has the value `1`. `1` means Prometheus can reach the target. `0` means it cannot.

### Check 2: What is happening?

```
sum(rate(app_http_requests_total[1m]))
```

The traffic of the whole app, per second (about 2 per second).

```
sum(rate(app_http_requests_total{status="500"}[1m])) / sum(rate(app_http_requests_total[1m]))
```

The share of requests that fail. In our app it is about `0.09`, which is 9%. The traffic generator calls `/error` on purpose, one request out of every five.

### Check 3: Why?

In Grafana, open **Explore**, choose **loki**, and run:

```
{service="sample-app"} |= "error"
```

You see the error lines. This is our normal level of errors. Now we will make it worse.

---

## Step 2: Problem 1, a burst of errors

We will send 200 error requests in a few seconds. We use the `traffic` container, because it already has `curl` and it can reach the app.

```bash
docker compose exec traffic sh -c 'for i in $(seq 1 200); do curl -s http://sample-app:8000/error > /dev/null; done'
```

Now find the problem **like in a real incident**. Wait about 30 seconds so Prometheus collects new data, then follow the checklist.

### What changed? (metrics)

In Grafana, open the **Sample App Health** dashboard (or use Explore with the Prometheus data source). Set the time range to **Last 5 minutes**. You see the errors jump up.

Or in Prometheus, run:

```
sum(rate(app_http_requests_total{status="500"}[1m]))
```

The error rate jumps from about 0.2 to a much higher value, and then comes back down.

### Why? (logs)

Now we need the reason. Go to **Explore**, data source **loki**:

```
{service="sample-app"} |= "error"
```

Every line says `database connection refused`, on the path `/error`. And the time of the first line is the moment the burst began.

Count them in numbers, with `count_over_time`:

```
sum(count_over_time({service="sample-app"} |= "error" [1m]))
```

You see a high bar, at the same time as the metric jump. **The metric and the log tell the same story.** The metric told us **what** (errors jumped). The log told us **why** (database connection refused).

---

## Step 3: Problem 2, the app goes down

Now a bigger problem: the app stops completely.

```bash
docker compose stop sample-app
```

### Check 1: Is it up?

Open http://localhost:9090/targets. The target `sample-app` becomes **DOWN**. Or run in Prometheus:

```
up{job="sample-app"}
```

The value is now `0`.

### Is anyone told? (alert)

Open http://localhost:9090/alerts. `SampleAppDown` goes **Pending** (yellow), because the rule has `for: 30s`. After about 45 to 60 seconds it becomes **Firing** (red).

Open http://localhost:9093 (Alertmanager). The alert is shown there too.

### Why? (logs)

```
{service="sample-app"}
```

The logs of the app **stop** at the moment it was stopped. A log that goes quiet is also information.

The logs of the other services (`alloy`, `loki`, `grafana`) are still there. Only the stopped service is quiet.

### Fix it and verify

```bash
docker compose start sample-app
```

Wait about 30 seconds. Then check:

- Targets: `sample-app` is **UP** again.
- Alerts: `SampleAppDown` goes back to **inactive**. (In Alertmanager it is **resolved**.)
- Explore: `{service="sample-app"}` shows new lines starting from the restart.

Always **verify**: do not stop at "I fixed it". Check that the metric, the alert and the logs are back to normal.

---

## Common causes: what to check when something breaks

| You see | Most likely cause | First thing to check |
|---------|-------------------|---------------------|
| Target is DOWN | The service is stopped, or the address is wrong | `docker compose ps`, then the address in `prometheus.yml` |
| Target is UP but no data in Grafana | Wrong data source, or wrong time range | The data source name and the time range at the top right |
| Error rate is high | The app has a problem | The logs: `{service="..."} \|= "error"` |
| No logs for a service | Alloy cannot read it, or the service is quiet | `docker compose logs alloy`, then the Alloy page at http://localhost:12345 |
| Alert does not fire | The rule is wrong, or the `for:` time has not passed | http://localhost:9090/alerts and the rule in `alert-rules.yml` |
| Alert fires but no message arrives | Alertmanager has no receiver | `alertmanager.yml` (in this lab we only show alerts, we do not send them) |
| Panel says "No data" | The query is wrong, or nothing matches | Run the same query in Explore |

---

## Step 4: Clean up

You finished the course labs. To stop everything and remove the containers:

```bash
docker compose down
```

Your Grafana dashboards stay in the Docker volume. To remove them too (this deletes your dashboard):

```bash
docker compose down -v
```

## Commands you used

| Command | What it does |
|---------|--------------|
| `docker compose up -d --build` | Start everything |
| `docker compose ps` | Show running services |
| `docker compose exec traffic sh -c '...'` | Run a command inside a running container |
| `docker compose stop sample-app` | Stop one service (it simulates a crash) |
| `docker compose start sample-app` | Start it again (the fix) |
| `docker compose logs <service>` | Show the logs of a service in the terminal |
| `docker compose down` | Stop and remove the containers |

## Words to remember

| Word | Meaning |
|------|---------|
| Incident | A problem that affects users, and needs action |
| Normal state | How the system looks when it is healthy. You need it to see a problem |
| Target | Something Prometheus scrapes. `up` tells if it works |
| Pending, Firing, Resolved | The three states of an alert |
| Verify | Check that metrics, alerts and logs are back to normal after a fix |

## What next?

You have built a full monitoring stack: metrics, alerts and logs. Ideas to continue on your own:

- Add a second alert, for a high error ratio.
- Monitor an app of your own. Add one more `scrape_config` in `prometheus.yml`.
- Make a dashboard with `up`, requests, errors, and logs side by side.
