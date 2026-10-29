from flask import jsonify


class ApiError(Exception):
    """Raised to produce a consistent JSON error response."""

    def __init__(self, message, status_code=400, errors=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.errors = errors

    def to_response(self):
        payload = {"error": self.message}
        if self.errors:
            payload["details"] = self.errors
        return jsonify(payload), self.status_code


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return err.to_response()

    @app.errorhandler(404)
    def handle_404(err):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def handle_405(err):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def handle_500(err):
        return jsonify({"error": "Internal server error"}), 500
