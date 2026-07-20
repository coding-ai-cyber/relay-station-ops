import uuid
from datetime import datetime

from pydantic import BaseModel


class FileRead(BaseModel):
    id: uuid.UUID
    original_name: str
    content_type: str | None
    size_bytes: int | None
    uploaded_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
