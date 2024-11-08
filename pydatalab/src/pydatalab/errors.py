import os
from typing import Any, Callable, Iterable, Tuple

from flask import Response, jsonify
from pydantic import ValidationError
from werkzeug.exceptions import Forbidden, HTTPException, RequestEntityTooLarge


class UserRegistrationForbidden(Forbidden):
    """Raised when a user tries to register via OAuth without the appropriate
    properties/credentials, e.g., public membership of a GitHub organization
    that is on the allow list.
    """

    description: str = """<html><head></head>
    <body>
    <h1>403 Forbidden</h1>

<h2>Unable to create account</h2>

<p>No user data will be stored as a result of this interaction, but you may wish to clear your cookies for this site.</p>

<p>
The OAuth identity used for registration is not on the allow list.
If you believe this to be an error, please first verify with the deployment manager
that you are allowed to make an account.
</p>

<p>If this was not an error, you may wish to revoke any permissions given to the datalab OAuth application.</p>
</body>
</html>
"""


def handle_http_exception(exc: HTTPException) -> Tuple[Response, int]:
    """Return a specific error message and status code if the exception stores them."""
    response = {
        "title": exc.__class__.__name__,
        "description": exc.description,
    }
    status_code = exc.code if exc.code else 400

    return jsonify(response), status_code


def render_unauthorised_user_template(exc: UserRegistrationForbidden) -> Tuple[Response, int]:
    """Return a rich HTML page on user account creation failure."""
    return Response(response=exc.description), exc.code


def handle_large_file_exception(exc: RequestEntityTooLarge) -> Tuple[Response, int]:
    """Return a JSON response with a specific error message about file size."""
    from pydatalab.config import CONFIG

    response = {
        "title": exc.__class__.__name__,
        "status": "error",
        "description": f"""Uploaded file is too large.
The maximum file size is {CONFIG.MAX_CONTENT_LENGTH / 1024 ** 3:.2f} GB.
Contact your datalab administrator if you need to upload larger files.""",
    }
    return jsonify(response), 413


def handle_pydantic_validation_error(exc: ValidationError) -> Tuple[Response, int]:
    """Handle pydantic validation errors separately from other exceptions.
    These always come from malformed data, so should not necessarily trigger the
    Flask debugger.
    """
    response = {
        "title": exc.__class__.__name__,
        "message": str(exc.args[:]) if exc.args else "",
    }
    return jsonify(response), 500


def handle_generic_exception(exc: Exception) -> Tuple[Response, int]:
    """Return a specific error message and status code if the exception stores them."""
    if os.environ.get("FLASK_ENV") == "development":
        raise exc

    response = {
        "title": exc.__class__.__name__,
        "message": str(exc.args) if exc.args else "",
    }
    return jsonify(response), 500


ERROR_HANDLERS: Iterable[Tuple[Any, Callable[[Any], Tuple[Response, int]]]] = [
    (UserRegistrationForbidden, render_unauthorised_user_template),
    (RequestEntityTooLarge, handle_large_file_exception),
    (HTTPException, handle_http_exception),
    (ValidationError, handle_pydantic_validation_error),
    (Exception, handle_generic_exception),
]
