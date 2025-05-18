from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from models.response import ApiResponse
from fastapi.exceptions import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Validation hatalarını yönetir."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(x) for x in error["loc"])
        message = error["msg"]
        errors.append(f"{field}: {message}")

    error_message = " | ".join(errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ApiResponse.error_response(
            message=error_message,
            code=status.HTTP_422_UNPROCESSABLE_ENTITY
        ).model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP hatalarını yönetir."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )

async def method_not_allowed_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 405 Method Not Allowed hatalarını yönetir."""
    if exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        response = ApiResponse(
            success=False,
            message=f"Bu endpoint için {request.method} metodu desteklenmiyor. Lütfen doğru HTTP metodunu kullanın.",
            code=status.HTTP_405_METHOD_NOT_ALLOWED,
            data=None
        )
        return JSONResponse(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            content=response.model_dump()
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    ) 