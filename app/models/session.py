from datetime import datetime
from pydantic import BaseModel


class SessionCreate(BaseModel):
    token_hash: str
    user_id: str
    csrf_token: str
    created_at: datetime
    expires_at: datetime
