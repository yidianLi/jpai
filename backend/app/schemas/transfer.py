from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TransferCreate(BaseModel):
    asset_id: int
    target_company_id: Optional[int] = None
    target_dept_id: int
    target_position: Optional[str] = Field(default=None, max_length=128)
    target_user_name: Optional[str] = Field(default=None, max_length=64)
    reason: Optional[str] = Field(default=None, max_length=512)
    estimated_saving: Optional[Decimal] = None


class TransferDecision(BaseModel):
    remark: Optional[str] = Field(default=None, max_length=512)


class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_id: int
    source_dept_name: Optional[str]
    target_dept_name: str
    target_position: Optional[str]
    target_user_name: Optional[str]
    reason: Optional[str]
    estimated_saving: Optional[Decimal]
    status: str
    receiver_remark: Optional[str]
    receiver_time: Optional[datetime]
    operator_time: Optional[datetime]
    created_at: datetime
