from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str


class MessageResponse(BaseModel):
    message: str
