"""
User profile and eligibility history models.

UserProfile stores the user's demographic details for quick re-checks.
EligibilityHistory records every eligibility check with profile and results snapshots.
"""

from datetime import datetime

from sqlalchemy import String, Float, Boolean, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserProfile(Base):
    """
    Saved user profile linked 1:1 with a User account.

    Stores the same fields used for eligibility checking so the user
    doesn't have to re-enter them every time.
    """

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    gender: Mapped[str] = mapped_column(String(20), nullable=True)
    annual_income: Mapped[float] = mapped_column(Float, nullable=True)
    state: Mapped[str] = mapped_column(String(100), nullable=True)
    caste_category: Mapped[str] = mapped_column(String(20), nullable=True)
    occupation: Mapped[str] = mapped_column(String(50), nullable=True)
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_minority: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bpl: Mapped[bool] = mapped_column(Boolean, default=False)
    is_student: Mapped[bool] = mapped_column(Boolean, default=False)
    is_senior_citizen: Mapped[bool] = mapped_column(Boolean, default=False)
    land_owned_acres: Mapped[float] = mapped_column(Float, nullable=True)
    num_children: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"


class EligibilityHistory(Base):
    """
    Record of a past eligibility check.

    Stores both the profile snapshot and results snapshot as JSON text
    so historical data remains accurate even if the user updates their profile
    or schemes change.
    """

    __tablename__ = "eligibility_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_snapshot: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    results_snapshot: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    total_matched: Mapped[int] = mapped_column(Integer, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="eligibility_history")

    def __repr__(self) -> str:
        return (
            f"<EligibilityHistory(id={self.id}, user_id={self.user_id}, "
            f"matched={self.total_matched})>"
        )
