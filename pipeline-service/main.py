import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models.customer import Customer
from services.ingestion import fetch_all_customers, upsert_customers

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("pipeline-service")


# Startup — create tables if they don't exist
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables if not exists...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database ready.")
    yield


# App
app = FastAPI(
    title="Customer Pipeline Service",
    version="1.0.0",
    description="Ingests customer data from Flask mock server into PostgreSQL.",
    lifespan=lifespan,
)


@app.post("/api/ingest")
async def ingest(db: Session = Depends(get_db)):
    """
    Fetch all customers from the Flask mock server (handles pagination
    automatically) and upsert them into PostgreSQL.
    Safe to call multiple times — upsert ensures no duplicates.
    """
    try:
        records = await fetch_all_customers()
        count   = upsert_customers(db, records)
        return {"status": "success", "records_processed": count}
    except Exception as exc:
        logger.exception("Ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(exc)}")


@app.get("/api/customers")
def list_customers(
    page:  int = 1,
    limit: int = 10,
    db:    Session = Depends(get_db),
):
    """
    Paginated customer list from PostgreSQL.
    """
    page  = max(1, page)
    limit = max(1, min(100, limit))

    total    = db.query(Customer).count()
    pages    = max(1, -(-total // limit))
    offset   = (page - 1) * limit
    customers = (
        db.query(Customer)
        .order_by(Customer.customer_id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "data":  [c.to_dict() for c in customers],
        "total": total,
        "page":  page,
        "limit": limit,
        "pages": pages,
    }


@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """
    Single customer lookup by customer_id from PostgreSQL.
    """
    customer = db.query(Customer).filter(
        Customer.customer_id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer '{customer_id}' not found."
        )

    return {"data": customer.to_dict()}