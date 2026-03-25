from sqlalchemy import Column, Date, DateTime, Numeric, String, Text
from database import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id     = Column(String(50),      primary_key=True)
    first_name      = Column(String(100),     nullable=False)
    last_name       = Column(String(100),     nullable=False)
    email           = Column(String(255),     nullable=False)
    phone           = Column(String(20))
    address         = Column(Text)
    date_of_birth   = Column(Date)
    account_balance = Column(Numeric(15, 2))
    created_at      = Column(DateTime)

    def to_dict(self) -> dict:
        """Serialize model to dict for JSON responses."""
        return {
            "customer_id":     self.customer_id,
            "first_name":      self.first_name,
            "last_name":       self.last_name,
            "email":           self.email,
            "phone":           self.phone,
            "address":         self.address,
            "date_of_birth":   str(self.date_of_birth) if self.date_of_birth else None,
            "account_balance": float(self.account_balance) if self.account_balance else None,
            "created_at":      str(self.created_at) if self.created_at else None,
        }