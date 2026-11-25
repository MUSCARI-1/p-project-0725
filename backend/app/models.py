from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .extensions import db


class Policy(db.Model):
    __tablename__ = "policies"

    policy_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    keywords: Mapped[str] = mapped_column(String(500), default="")
    category: Mapped[str] = mapped_column(String(50), default="", index=True)
    sub_category: Mapped[str] = mapped_column(String(100), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    support: Mapped[str] = mapped_column(Text, default="")

    apply_period_code: Mapped[str] = mapped_column(String(10), default="")
    apply_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    apply_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    apply_method: Mapped[str] = mapped_column(Text, default="")
    screening_method: Mapped[str] = mapped_column(Text, default="")
    documents_text: Mapped[str] = mapped_column(Text, default="")
    apply_url: Mapped[str] = mapped_column(String(1000), default="")
    ref_url: Mapped[str] = mapped_column(String(1000), default="")
    ref_url2: Mapped[str] = mapped_column(String(1000), default="")

    # None이면 나이 제한이 없다
    min_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    max_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    marital_code: Mapped[str] = mapped_column(String(10), default="")
    job_codes: Mapped[str] = mapped_column(String(200), default="")
    school_codes: Mapped[str] = mapped_column(String(200), default="")
    major_codes: Mapped[str] = mapped_column(String(200), default="")
    special_codes: Mapped[str] = mapped_column(String(200), default="")
    income_cond_code: Mapped[str] = mapped_column(String(10), default="")
    # 단위는 만 원이다
    income_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    income_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    income_text: Mapped[str] = mapped_column(Text, default="")

    extra_qualification: Mapped[str] = mapped_column(Text, default="")
    excluded_targets: Mapped[str] = mapped_column(Text, default="")
    etc: Mapped[str] = mapped_column(Text, default="")

    supervising_org: Mapped[str] = mapped_column(String(255), default="")
    operating_org: Mapped[str] = mapped_column(String(255), default="")

    raw: Mapped[dict] = mapped_column(JSON)
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime)


# zipCd, lclsfNm에 값이 콤마로 여러 개 들어 있어서 별도 테이블로 분리한다
class PolicyRegion(db.Model):
    __tablename__ = "policy_regions"

    policy_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("policies.policy_id", ondelete="CASCADE"), primary_key=True
    )
    region_code: Mapped[str] = mapped_column(String(10), primary_key=True, index=True)


class PolicyCategory(db.Model):
    __tablename__ = "policy_categories"

    policy_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("policies.policy_id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
