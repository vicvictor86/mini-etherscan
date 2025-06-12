from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number, must be at least 1")
    per_page: int = Field(
        default=10, ge=1, description="Number of items per page, must be at least 1"
    )
