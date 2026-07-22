from typing import Any
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

def generate_response(
    succeeded: bool = True,
    entity: dict[str, Any] = None,
    error: str = None,
    exception_error: str = None,
    message: str = None
) -> JSONResponse:
    """
    Helper function to generate a consistent response format.

    :param succeeded: Boolean indicating if the operation was successful.
    :param entity: Dictionary containing details of the entity.
    :param error: String providing information about any error.
    :param exception_error: String detailing any exception error that occurred.
    :param message: String containing a message related to the response.
    :return: JSONResponse representing the response.
    """
    content = {
        "succeeded": succeeded,
        "entity": entity if entity is not None else {},
        "error": error,
        "exceptionError": exception_error,
        "message": message
    }
    return JSONResponse(content=jsonable_encoder(content))

def generate_error_response(exception_error: str, 
                            status_code: int,
                            message: str = None,
                            succeeded: bool = False, 
                            error: bool = True,
                            ) -> JSONResponse:
    """
    Helper function to generate a consistent error response format.

    :param succeeded: Boolean indicating if the operation was successful.
    :param error: String providing information about any error.
    :param exception_error: String detailing any exception error that occurred.
    :param message: Readablemessage related to the error response, to be displayed on UI.
    :param status_code: HTTP status code for the response.
    :return: JSONResponse representing the response.
    """
    content = {
        "succeeded": succeeded,
        "entity": {},
        "error": error,
        "exceptionError": exception_error,
        "message": message or f"Error Processing Request: {exception_error}",
        "statusCode": status_code
    }
    return JSONResponse(status_code=status_code, content=jsonable_encoder(content))

