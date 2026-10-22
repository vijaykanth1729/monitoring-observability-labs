# Module 2: Beginner PromQL

In module 1 we collected metrics. In this lab we **ask questions** about them.

The language for asking is **PromQL**. You type a query in the Prometheus web page and you get an answer.

By the end you can answer three real questions:

1. Is my app up?
2. How many requests per second is it getting?
3. What share of those requests are failing?

## Before you start

- Docker is running (see the main README).
- You finished module 1, or at least have the whole repository on your laptop. This lab reuses the sample app from `module-01-prometheus-and-setup`.
- Ports 8000, 9090 and 9100 must be free. If the module 1 stack is still running, stop it first: open a terminal in `module-01-prometheus-and-setup/step-4-all-together` and run `docker compose down`. Not sure? `docker ps` shows what is running.

Open a terminal in this folder (`module-02-beginner-promql`).

## The plan

| Step | What you do |
|------|-------------|
| 0 | Start the stack. A small traffic helper sends requests, so there is something to look at |
| 1 | Query `up` |
| 2 | Query a metric that has labels |
| 3 | Filter by labels |
| 4 | Counters and `rate()` |
| 5 | Add things together with `sum` |
| 6 | Answer a health question |
| 7 | Break something and watch the query change |

---

## Step 0: Start the stack

### The file

`docker-compose.yml` has the three services from module 1, plus one new service called `traffic`.

```yaml
  traffic:
    image: curlimages/curl:8.14.1
    depends_on:
      - sample-app
    entrypoint:
      - sh
      - -c
      - |
        i=0
        while true; do
          curl -s http://sample-app:8000/ > /dev/null
          curl -s http://sample-app:8000/work > /dev/null
          i=$$((i+1))
          if [ $$((i % 5)) -eq 0 ]; then
            curl -s http://sample-app:8000/error > /dev/null
          fi
          sleep 1
        done
```

### What is new

| Line | Meaning |
|------|---------|
| `curlimages/curl` | A tiny image that has the `curl` tool. `curl` opens a web page from the command line. |
| `depends_on: - sample-app` | Start the sample app first. |
| `entrypoint:` | The command this container runs. Here it is a small loop. |
| `curl -s http://sample-app:8000/work` | Open the page of the sample app. We use the service name `sample-app` as the address, just like Prometheus does. |
| `i % 5` | Every fifth round, also open `/error`. |
| `sleep 1` | Wait one second, then repeat. |

So the loop visits `/` and `/work` all the time, and `/error` once in every five rounds. That gives us a steady stream of normal requests and a few errors, with no work from you.

`$$` is how Compose writes a single `$`. You can ignore that detail.

### Run it

```bash
docker compose up -d --build
docker compose ps
```

You should see four services running.

**Wait two minutes.** Prometheus needs a few scrapes before some queries have enough data.

Open http://localhost:9090/targets and check that all three targets are **UP**.

### Where do I type queries?

Open http://localhost:9090. This is the **Query** page (older versions call it **Graph**).

- Type a query in the box.
- Click **Execute**.
- The **Table** tab shows the current value. The **Graph** tab shows values over time.

---

## Step 1: Query `up`

Type this and click **Execute**:

```
up
```

You get three rows, one for each target. Each row has a value.

| Part | Example | Meaning |
|------|---------|---------|
| Metric name | `up` | What we measure |
| Labels | `{job="sample-app", instance="sample-app:8000"}` | Which target |
| Value | `1` | `1` = last scrape worked, `0` = it failed |

Every target gets its own row, because every target is its own **time series**.

Now ask only about the sample app:

```
up{job="sample-app"}
```

The part in `{ }` is a **filter**. You get one row. Click the **Graph** tab to see a flat line at 1.

---

## Step 2: A metric with labels

```
app_http_requests_total
```

You get one row for each combination of labels, something like this:

```
app_http_requests_total{method="GET", path="/", status="200"}        152
app_http_requests_total{method="GET", path="/work", status="200"}    152
app_http_requests_total{method="GET", path="/error", status="500"}    30
```

- The name ends with `_total`. This is a **counter**. It only goes up, and it counts since the app started.
- The labels tell us which path and which status.

Your numbers will be different. They grow every second.

---

## Step 3: Filter with labels

You can pick rows by their labels. There are four operators:

| Operator | Meaning | Example |
|----------|---------|---------|
| `=` | equals | `status="500"` |
| `!=` | not equal | `status!="200"` |
| `=~` | matches a pattern | `path=~"/w.*"` (paths that start with /w) |
| `!~` | does not match a pattern | `path!~"/work"` |

Try each one:

```
app_http_requests_total{path="/error"}
```

```
app_http_requests_total{status!="200"}
```

```
app_http_requests_total{path=~"/w.*"}
```

Each time, fewer rows come back. Filtering is how you go from "everything" to "the thing I care about".

---

## Step 4: Counters and `rate()`

A counter such as `app_http_requests_total` only goes up. Look at it in the **Graph** tab: a line that climbs forever.

A big number like 152 does not tell us if the app is busy **now**. We want to know: how many requests **per second**?

That is what `rate()` does:

```
rate(app_http_requests_total[1m])
```

| Part | Meaning |
|------|---------|
| `[1m]` | Look at the last 1 minute of data |
| `rate(...)` | Work out how fast the counter grew, per second |

The graph is now flat, near a steady number. Each row is the requests per second for one path. Expect about `0.8` for `/` and `/work`, and about `0.16` for `/error`.

Rule to remember: **for a counter, always use `rate()`.** A raw counter hides what is happening now.

### Counter or gauge?

Not every metric is a counter. A **gauge** goes up and down, like memory. For a gauge we read the value directly, without `rate()`.

```
node_memory_MemAvailable_bytes
```

Memory goes up and down, so this is a gauge.

---

## Step 5: Add things up with `sum`

Step 4 gave one row per label combination. Often we want one number.

```
sum(rate(app_http_requests_total[1m]))
```

This is the total requests per second for the whole app. Expect about `1.8`.

Or one number for each path:

```
sum by (path) (rate(app_http_requests_total[1m]))
```

`by (path)` means: add everything up, but keep one row for each `path`.

Try `sum by (status)` too. Which status codes does our app return?

---

## Step 6: Answer a health question

Now we use what we learned. Question: **what share of requests are failing?**

First, errors per second. Errors are status `500`:

```
sum(rate(app_http_requests_total{status="500"}[1m]))
```

Then divide errors by all requests:

```
sum(rate(app_http_requests_total{status="500"}[1m]))
/
sum(rate(app_http_requests_total[1m]))
```

Expect about `0.09`. That is 9 percent, or about 1 request in 11. Our traffic helper makes exactly one error for every ten good requests.

You can write the query on one line or many. Prometheus does not mind.

This is the shape of most real health checks: **errors divided by total**.

---

## Step 7: Break it and watch

Stop the sample app:

```bash
docker compose stop sample-app
```

Wait about 30 seconds. Then run:

```
up{job="sample-app"}
```

The value is now `0`. The target is down. A query for every target that is down:

```
up == 0
```

`== 0` is a filter on the **value**. Only rows with value 0 stay.

Now start it again:

```bash
docker compose start sample-app
```

After 30 seconds `up == 0` returns nothing. All targets are healthy again.

Notice: the request counters restart from zero when the app restarts. That is another reason we use `rate()` and not raw counters.

---

## Clean up

```bash
docker compose down
```

## Cheat sheet

| I want to... | Query |
|--------------|-------|
| See if targets work | `up` |
| Only one job | `up{job="sample-app"}` |
| Only targets that are down | `up == 0` |
| Filter by label | `metric{label="value"}` |
| Requests per second | `rate(app_http_requests_total[1m])` |
| One total number | `sum(rate(app_http_requests_total[1m]))` |
| One number per path | `sum by (path) (rate(app_http_requests_total[1m]))` |
| Share of requests that fail | errors per second divided by all requests per second |

## Words to remember

| Word | Meaning |
|------|---------|
| Query | A question typed in the Prometheus Query page |
| Selector | A metric name with optional `{ }` filters |
| Counter | A number that only goes up. Use `rate()` |
| Gauge | A number that goes up and down. Read it directly |
| `rate()` | Per-second speed of a counter |
| `sum by` | Add up, but keep chosen labels |

## Common problems

| You see | What to do |
|---------|-----------|
| `Empty query result` | The name or label is wrong, or there is not enough data yet. Wait 2 minutes, check spelling |
| `rate()` returns nothing | The `[1m]` window needs a few scrapes. Wait a little |
| `port is already allocated` | Run `docker compose down` in the module 1 folder you used before |
| Error rows are missing | Wait one more minute. The first `/error` call comes after five rounds |
