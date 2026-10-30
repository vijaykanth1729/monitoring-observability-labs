# Module 4: Simple alerting

A dashboard is great, but nobody can watch it all day and all night.

An **alert** turns the watching over to Prometheus. It checks a rule again and again, and it tells you when something is wrong.

In this lab you add one alert rule: **"the sample app is down"**. Then you break the app and watch the alert go through its states.

## Before you start

- Docker is running (see the main README).
- You have the whole repository on your laptop. This lab reuses the sample app from `module-01-prometheus-and-setup`.
- Ports 3000, 8000, 9090, 9093 and 9100 must be free. If the module 3 stack is still running, stop it first: open a terminal in `module-03-grafana-dashboards` and run `docker compose down`. Not sure? `docker ps` shows what is running.

Open a terminal in this folder (`module-04-simple-alerting`).

## The plan

| Step | What you do |
|------|-------------|
| 0 | Start the stack. It is the module 3 stack plus Alertmanager and one rule file |
| 1 | Read the alert rule |
| 2 | See the rule in Prometheus (inactive) |
| 3 | Break the app and watch: inactive, pending, firing |
| 4 | See the alert in Alertmanager |
| 5 | Fix the app and watch the alert resolve |

---

## Step 0: Start the stack

### What is new

Compared with module 3, three things are new:

| New thing | What it is |
|-----------|-----------|
| `alert-rules.yml` | The file that holds our alert rule |
| `alertmanager` service | A new program that receives alerts from Prometheus |
| `prometheus.yml` (changed) | It now knows where the rules file is, and where Alertmanager is |

In `docker-compose.yml`, Prometheus gets one more file, and there is one new service:

```yaml
  prometheus:
    image: prom/prometheus:v3.5.0
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./alert-rules.yml:/etc/prometheus/alert-rules.yml

  alertmanager:
    image: prom/alertmanager:v0.28.1
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
```

Both use a `volumes:` line like module 1: a file on your laptop shows up inside the container.

The Grafana volume at the bottom of the file has a fixed `name`. It is the same volume as module 3, so the dashboard you built is still there.

### The changes in `prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - /etc/prometheus/alert-rules.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]
```

| Line | Meaning |
|------|---------|
| `evaluation_interval: 15s` | Prometheus checks the alert rules every 15 seconds. (The normal default is one minute. We use 15 seconds so the lab is faster.) |
| `rule_files:` | Where the rules are, inside the container. |
| `alerting:` | Where to send alerts. The address is a service name again: `alertmanager:9093`. |

### Run it

```bash
docker compose up -d --build
docker compose ps
```

You should see six services running: sample-app, node-exporter, prometheus, alertmanager, grafana and traffic. If one is missing, run `docker compose ps -a` and `docker compose logs <name>`.

Open http://localhost:9090/targets and check that all three targets are **UP**.

---

## Step 1: Read the alert rule

Open `alert-rules.yml`:

```yaml
groups:
  - name: sample-app
    rules:
      - alert: SampleAppDown
        expr: up{job="sample-app"} == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Sample app is down"
          description: "Prometheus cannot scrape {{ $labels.instance }}."
```

| Line | Meaning |
|------|---------|
| `groups:` and `name:` | Rules live in groups. A group is just a named list. |
| `alert: SampleAppDown` | The name of the alert. |
| `expr: up{job="sample-app"} == 0` | The condition. It is a normal query from module 2. If it returns a row, the alert condition is true. Here: the sample app is down. |
| `for: 30s` | The condition must stay true for 30 seconds before the alert fires. This avoids false alarms from a short problem. |
| `labels:` | Extra labels on the alert, like `severity`. Used later for sorting and routing. |
| `annotations:` | Human text: a short summary and a longer description. `{{ $labels.instance }}` is replaced by the real instance name. |

You already know the most important line. The `expr` is the query `up{job="sample-app"} == 0` from module 2.

---

## Step 2: See the rule in Prometheus

Open http://localhost:9090/alerts

You see the group `sample-app` and the alert `SampleAppDown`. Its state is **inactive** (green). This means the condition is false: the app is up. Everything is fine.

---

## Step 3: Break the app, watch the three states

An alert has three states:

| State | Meaning |
|-------|---------|
| **Inactive** | The condition is false. All good. |
| **Pending** | The condition is true, but not yet for the full `for` time (30 seconds). Waiting. |
| **Firing** | The condition has been true for the full `for` time. The alert is active, and it is sent to Alertmanager. |

Stop the sample app:

```bash
docker compose stop sample-app
```

Now refresh http://localhost:9090/alerts every 10 seconds.

1. Within about 15 seconds the rule is checked and the alert turns **Pending** (yellow).
2. After the 30 seconds of `for`, it turns **Firing** (red).

In total it takes about one minute. The wait is on purpose: if the app only had a short problem, there would be no alarm.

Click the alert to see its labels and the annotations (summary and description).

---

## Step 4: See the alert in Alertmanager

Open http://localhost:9093

You see the alert `SampleAppDown`, with its labels.

### What Alertmanager does

| Prometheus | Alertmanager |
|------------|-------------|
| Checks the rules and decides that an alert is firing | Receives alerts, groups similar ones, and decides who to tell |

Alertmanager can send to email, Slack, PagerDuty and more. In this course we do not set that up. Our `alertmanager.yml` only has a receiver with a name and nothing else:

```yaml
route:
  receiver: default

receivers:
  - name: default
```

So the alert arrives, and you can see it, but nobody is notified. That is enough to learn how it works.

---

## Step 5: Fix it, watch it resolve

Start the app again:

```bash
docker compose start sample-app
```

Refresh the Prometheus Alerts page after about 30 seconds. The alert is **Inactive** again. After a short time, it disappears from Alertmanager too. This is called **resolved**.

---

## What makes a good alert

- Alert on things that **hurt users**, such as the app being down or many errors, not on every small change.
- Every alert should need **an action**. If nobody needs to do anything, it is not an alert, it is a dashboard panel.
- Use `for:` so short problems do not wake someone at night.

## Try it yourself (optional)

Change `for: 30s` to `for: 2m`, restart Prometheus (`docker compose restart prometheus`) and break the app again. How long does the Pending state last now?

## Clean up

```bash
docker compose down
```

## Commands you used

| Command | What it does |
|---------|--------------|
| `docker compose up -d --build` | Start everything |
| `docker compose stop sample-app` | Stop the app, to break it |
| `docker compose start sample-app` | Start it again |
| `docker compose restart prometheus` | Restart Prometheus after a file change |
| `docker compose down` | Stop and remove the containers |

## Words to remember

| Word | Meaning |
|------|---------|
| Alert rule | A condition (a query) that Prometheus checks again and again |
| Inactive | The condition is false |
| Pending | The condition is true, but the `for` time is not finished |
| Firing | The condition has been true for the `for` time. The alert is active |
| Resolved | The condition became false again |
| Alertmanager | The program that receives alerts and decides who to tell |
| Annotation | Human text attached to an alert |

## Common problems

| You see | What to do |
|---------|-----------|
| No alert on the Alerts page | Check `docker compose logs prometheus`. Most often there is a spelling or indentation mistake in `alert-rules.yml` |
| Alert stays Inactive after stopping the app | Wait one minute. Check the Targets page: the sample app should be DOWN |
| Alertmanager page is empty | The alert must be **Firing**, not only Pending. Wait a little |
| `port is already allocated` | Run `docker compose down` in the module 3 folder |
| Dashboard is empty in Grafana | You did not do module 3 on this laptop, so there is no dashboard yet. That is fine |
