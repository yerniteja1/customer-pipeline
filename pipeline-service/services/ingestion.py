import logging
from datetime import datetime, date

import httpx
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from models.customer import Customer

logger = logging.getLogger("pipeline-service")

MOCK_SERVER_URL = "http://mock-server:5000"
PAGE_LIMIT      = 10


# Step 1 — Fetch all pages from Flask
async def fetch_all_customers() -> list[dict]:
    all_records = []
    page        = 1

    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            response = await client.get(
                f"{MOCK_SERVER_URL}/api/customers",
                params={"page": page, "limit": PAGE_LIMIT},
            )
            response.raise_for_status()
            body = response.json()

            records = body.get("data", [])

            # no more records — we've consumed all pages
            if not records:
                break

            all_records.extend(records)
            logger.info("Fetched page %d — %d records", page, len(records))

            # stop if we've already fetched everything
            if len(all_records) >= body.get("total", 0):
                break

            page += 1

    logger.info("Total fetched from Flask: %d records", len(all_records))
    return all_records


# Step 2 — Upsert into PostgreSQL
def _parse_record(raw: dict) -> dict:
    return {
        "customer_id":     raw["customer_id"],
        "first_name":      raw["first_name"],
        "last_name":       raw["last_name"],
        "email":           raw["email"],
        "phone":           raw.get("phone"),
        "address":         raw.get("address"),
        "date_of_birth":   date.fromisoformat(raw["date_of_birth"])
                           if raw.get("date_of_birth") else None,
        "account_balance": raw.get("account_balance"),
        "created_at":      datetime.fromisoformat(
                               raw["created_at"].replace("Z", "+00:00")
                           ) if raw.get("created_at") else None,
    }


def upsert_customers(db: Session, records: list[dict]) -> int:
    if not records:
        return 0

    parsed = [_parse_record(r) for r in records]

    stmt = insert(Customer).values(parsed)

    # on duplicate customer_id → update all non-PK columns
    stmt = stmt.on_conflict_do_update(
        index_elements=["customer_id"],
        set_={
            "first_name":      stmt.excluded.first_name,
            "last_name":       stmt.excluded.last_name,
            "email":           stmt.excluded.email,
            "phone":           stmt.excluded.phone,
            "address":         stmt.excluded.address,
            "date_of_birth":   stmt.excluded.date_of_birth,
            "account_balance": stmt.excluded.account_balance,
            "created_at":      stmt.excluded.created_at,
        },
    )

    db.execute(stmt)
    db.commit()

    logger.info("Upserted %d records into PostgreSQL", len(parsed))
    return len(parsed)