from sqlalchemy import String
from sqlalchemy.orm import mapped_column, relationship

from app.db import Base


class Product(Base):
    # in all current cases this is the Stripe 'price' id
    id = mapped_column(String, primary_key=True)

    name = mapped_column(String, nullable=False)

    subscriptions = relationship("Subscription", back_populates="product")

    def __repr__(self):
        return f"<Product '{self.name}'>"
