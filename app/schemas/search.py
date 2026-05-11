from pydantic import BaseModel
from app.schemas.paper import PaperOut


class SemanticSearchRequest(BaseModel):
    query: str


class PolicySearchRequest(BaseModel):
    query: str
    ministry: str | None = None


class SemanticSearchResult(BaseModel):
    paper: PaperOut
    score: float


class PolicySearchResponse(BaseModel):
    brief_id: str
    message: str
