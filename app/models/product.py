from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.db import Base


class Product(Base):
    # in all current cases this is to the be a Stripe 'price' id
    id = Column(String, primary_key=True)

    name = Column(String, nullable=False)

    subscriptions = relationship("Subscription", back_populates="product")

    def __repr__(self):
        return f"<Product '{self.name}'>"
