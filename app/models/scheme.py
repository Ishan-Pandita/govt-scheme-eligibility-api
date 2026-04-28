"""
Scheme database model.

Stores government scheme details — name, ministry, benefits, apply links.
Linked to EligibilityCriteria for rule-engine evaluation and to States
via a many-to-many junction table.
"""

from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    Table,
    Column,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Many-to-many junction table: Scheme <-> State
scheme_state = Table(
    "scheme_states",
    Base.metadata,
    Column("scheme_id", Integer, ForeignKey("schemes.id", ondelete="CASCADE"), primary_key=True),
    Column("state_id", Integer, ForeignKey("states.id", ondelete="CASCADE"), primary_key=True),
)


class State(Base):
    """Indian state or union territory."""

    __tablename__ = "states"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False
    )  # e.g., "TN", "MH"

    # Relationships
    schemes: Mapped[list["Scheme"]] = relationship(
        secondary=scheme_state, back_populates="states"
    )

    def __repr__(self) -> str:
        return f"<State(id={self.id}, name={self.name}, code={self.code})>"


class Scheme(Base):
    """
    Government scheme with metadata.

    Each scheme has multiple EligibilityCriteria rows that the rule engine
    evaluates against a user profile.
    """

    __tablename__ = "schemes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    ministry: Mapped[str] = mapped_column(String(300), nullable=True)
    scheme_type: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # "central", "state", "both"
    benefit_amount: Mapped[str] = mapped_column(
        String(200), nullable=True
    )  # Free-text: "₹6,000/year", "Up to ₹2.5 lakh"
    benefit_description: Mapped[str] = mapped_column(Text, nullable=True)
    apply_link: Mapped[str] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    category: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # "agriculture", "health", "education", etc.
    gender_specific: Mapped[str] = mapped_column(
        String(20), nullable=True
    )  # "male", "female", or null for all
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    criteria: Mapped[list["EligibilityCriteria"]] = relationship(
        back_populates="scheme", cascade="all, delete-orphan"
    )
    states: Mapped[list["State"]] = relationship(
        secondary=scheme_state, back_populates="schemes"
    )

    def __repr__(self) -> str:
        return f"<Scheme(id={self.id}, name={self.name})>"
