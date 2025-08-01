from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Product(Base):
    # in all current cases this is the Stripe 'price' id
    id: Mapped[str] = mapped_column(String, primary_key=True)

    name: Mapped[str] = mapped_column(String, nullable=False)

    subscriptions = relationship("Subscription", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product '{self.name}'>"
