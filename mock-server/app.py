import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g, jsonify, request

# Logging — structured, timestamped
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("mock-server")

# App + constants
app = Flask(__name__)

_SERVICE    = "customer-mock-server"
_VERSION    = "1.0.0"
_START_TIME = time.time()
_DATA_PATH  = Path(__file__).parent / "data" / "customers.json"


# Data — loaded ONCE at startup
def _load_data() -> tuple[list[dict], dict[str, dict]]:
    """
    Load customers.json into memory.
    Builds a dict index for O(1) single-customer lookups.
    Crashes loudly at startup if the file is missing — fail fast.
    """
    if not _DATA_PATH.exists():
        logger.critical("customers.json not found at %s", _DATA_PATH)
        raise SystemExit(1)

    with _DATA_PATH.open(encoding="utf-8") as fh:
        records: list[dict] = json.load(fh)

    index: dict[str, dict] = {c["customer_id"]: c for c in records}
    logger.info("Loaded %d customer records from %s", len(records), _DATA_PATH)
    return records, index


CUSTOMERS, CUSTOMER_INDEX = _load_data()


# Request lifecycle hooks
@app.before_request
def _before():
    """Stamp every request with a unique ID and a start timer."""
    g.req_id    = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    g.req_start = time.perf_counter()


@app.after_request
def _after(response):
    """Inject tracing + timing headers; log the completed request."""
    elapsed_ms = round((time.perf_counter() - g.req_start) * 1000, 2)

    response.headers["X-Request-ID"]    = g.req_id
    response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
    response.headers["X-Service"]       = _SERVICE

    logger.info(
        "%-6s %-35s → %d  [%sms]  req=%s",
        request.method,
        request.path,
        response.status_code,
        elapsed_ms,
        g.req_id[:8],
    )
    return response


# Helpers
def _error(message: str, status_code: int):
    return jsonify({"error": message, "status_code": status_code}), status_code


def _paginate(items: list, page: int, limit: int) -> tuple[list, int]:
    page  = max(1, page)
    limit = max(1, min(100, limit))
    start = (page - 1) * limit
    return items[start : start + limit], len(items)


# Routes
@app.get("/api/health")
def health():
    return jsonify({
        "status":         "healthy",
        "service":        _SERVICE,
        "version":        _VERSION,
        "uptime_seconds": round(time.time() - _START_TIME, 2),
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "record_count":   len(CUSTOMERS),
    }), 200


@app.get("/api/customers")
def list_customers():
    # ── parse + validate query params ──
    try:
        page  = int(request.args.get("page",  1))
        limit = int(request.args.get("limit", 10))
    except ValueError:
        return _error("'page' and 'limit' must be integers.", 400)

    # ── optional search filter ──
    search  = request.args.get("search", "").strip().lower()
    dataset = CUSTOMERS

    if search:
        dataset = [
            c for c in CUSTOMERS
            if search in c["first_name"].lower()
            or search in c["last_name"].lower()
            or search in c["email"].lower()
        ]

    # ── paginate ──
    page_data, total = _paginate(dataset, page, limit)
    pages = max(1, -(-total // limit))

    return jsonify({
        "data":  page_data,
        "total": total,
        "page":  page,
        "limit": limit,
        "pages": pages,
    }), 200


@app.get("/api/customers/<string:customer_id>")
def get_customer(customer_id: str):
    customer = CUSTOMER_INDEX.get(customer_id)
    if not customer:
        return _error(f"Customer '{customer_id}' not found.", 404)

    return jsonify({"data": customer}), 200


# Global error handlers
@app.errorhandler(404)
def _404(_):
    return _error("Endpoint not found.", 404)

@app.errorhandler(405)
def _405(_):
    return _error("HTTP method not allowed.", 405)

@app.errorhandler(500)
def _500(exc):
    logger.exception("Unhandled server error: %s", exc)
    return _error("Internal server error.", 500)


if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info("Starting %s v%s on port %d", _SERVICE, _VERSION, port)
    app.run(host="0.0.0.0", port=port, debug=debug)