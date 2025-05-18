from typing import Generic, TypeVar, Optional
from pydantic import BaseModel
from fastapi import status, HTTPException

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    code: int
    data: Optional[T] = None

    @classmethod
    def success_response(
        cls,
        data: T,
        message: str = "İşlem başarılı",
        code: int = status.HTTP_200_OK
    ) -> "ApiResponse[T]":
        return cls(
            success=True,
            message=message,
            code=code,
            data=data
        )

    @classmethod
    def error_response(
        cls,
        message: str,
        code: int = status.HTTP_400_BAD_REQUEST,
        data: Optional[T] = None
    ) -> "ApiResponse[T]":
        raise HTTPException(
            status_code=code,
            detail=cls(
                success=False,
                message=message,
                code=code,
                data=data
            ).model_dump()
        )
    