import os
import random
import time

from flask import Flask, Response, g, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

app = Flask(__name__)

# ---------- Prometheus metrics ----------
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)


def endpoint_label():
    # Use the route pattern, not the raw path, to keep label cardinality low
    return request.url_rule.rule if request.url_rule else "unmatched"


@app.before_request
def start_timer():
    g.start = time.perf_counter()


@app.after_request
def record_metrics(response):
    if request.path != "/metrics":
        ep = endpoint_label()
        REQUESTS.labels(request.method, ep, response.status_code).inc()
        LATENCY.labels(ep).observe(time.perf_counter() - g.start)
    return response


# ---------- Routes ----------
@app.route("/")
def index():
    return jsonify(
        app="pulsewatch",
        version=os.getenv("APP_VERSION", "v1"),
        endpoints=["/health", "/metrics", "/slow", "/error", "/cpu"],
    )


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/slow")
def slow():
    """Sleeps a random time up to ?max= seconds (default 3). Use for latency alerts."""
    max_delay = min(float(request.args.get("max", 3)), 10)
    delay = random.uniform(0.2, max_delay)
    time.sleep(delay)
    return jsonify(delayed_seconds=round(delay, 2))


@app.route("/error")
def error():
    """Always returns 500. Use for error-rate alerts."""
    return jsonify(error="simulated failure"), 500


@app.route("/cpu")
def cpu():
    """Burns CPU for ?seconds= (default 2). Use for autoscaling tests."""
    seconds = min(float(request.args.get("seconds", 2)), 30)
    end = time.time() + seconds
    n = 0
    while time.time() < end:
        n += sum(i * i for i in range(1000))
    return jsonify(burned_seconds=seconds)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), threaded=True)
