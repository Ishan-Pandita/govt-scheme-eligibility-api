"""
EligibilityCriteria database model.

Each row represents one rule for a scheme. The rule engine evaluates
all criteria for a scheme against a user profile using the field/operator/value
pattern. This keeps the engine generic and data-driven — no hardcoded rules.

Supported operators: eq, neq, gte, lte, gt, lt, in, not_in, contains
"""

from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EligibilityCriteria(Base):
    """
    Single eligibility rule for a scheme.

    Example rows for PM Kisan:
        scheme_id=1, field="occupation",     operator="eq",  value="farmer"
        scheme_id=1, field="annual_income",  operator="lte", value="200000"
        scheme_id=1, field="age",            operator="gte", value="18"
    """

    __tablename__ = "eligibility_criteria"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    scheme_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # User profile field name: "age", "annual_income", "gender", "state", etc.
    operator: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "eq", "neq", "gte", "lte", "gt", "lt", "in", "not_in", "contains"
    value: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Stored as string, cast at runtime based on field type
    description: Mapped[str] = mapped_column(
        String(300), nullable=True
    )  # Human-readable: "Age must be 18 or older"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    scheme: Mapped["Scheme"] = relationship(back_populates="criteria")

    def __repr__(self) -> str:
        return (
            f"<EligibilityCriteria(id={self.id}, scheme_id={self.scheme_id}, "
            f"field={self.field}, operator={self.operator}, value={self.value})>"
        )
