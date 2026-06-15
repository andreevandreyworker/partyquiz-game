from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, code: str | None = None):
        self.code = code or self.__class__.code
        super().__init__(self.code)


class NotAuthenticatedError(AppError):
    status_code = 401
    code = "not_authenticated"


class RoomNotFoundError(AppError):
    status_code = 404
    code = "room_not_found"


class NotInRoomError(AppError):
    status_code = 403
    code = "not_in_room"


class NotHostError(AppError):
    status_code = 403
    code = "not_host"


class TooManyPendingError(AppError):
    status_code = 429
    code = "too_many_pending"


class EmptyQuestionError(AppError):
    status_code = 422
    code = "empty_question"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(
        request: Request, exc: AppError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code},
        )
