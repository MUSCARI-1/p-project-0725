from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, error: str, message: str, status: int = 400):
        super().__init__(message)
        self.error = error
        self.message = message
        self.status = status


def invalid(message: str) -> ApiError:
    return ApiError("INVALID_REQUEST", message, 400)


def not_found(message: str) -> ApiError:
    return ApiError("NOT_FOUND", message, 404)


_HTTP_CODES = {400: "INVALID_REQUEST", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 415: "INVALID_REQUEST"}


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _api_error(e: ApiError):
        return jsonify(error=e.error, message=e.message), e.status

    @app.errorhandler(HTTPException)
    def _http_error(e: HTTPException):
        code = _HTTP_CODES.get(e.code, "HTTP_ERROR")
        return jsonify(error=code, message=e.description), e.code

    @app.errorhandler(Exception)
    def _unexpected(e: Exception):
        app.logger.exception("처리되지 않은 오류")
        return jsonify(error="INTERNAL_ERROR", message="서버 내부 오류가 발생했습니다."), 500
