# =============================================================
# NEKOVA Web Framework — Router
# =============================================================
# Maps URL paths to handler functions.
#
# Example:
#   router.add("/hello", handler_fn, methods=["GET"])
#   router.handle(request) → calls handler_fn → response
#
# Supports:
#   - Static routes:   /hello
#   - Dynamic routes:  /user/<name>
#   - Multiple methods: GET, POST

import re
from nekova.web.request import NEKOVARequest
from nekova.web.response import (
    NEKOVAResponse, text_response,
    not_found_response, error_response
)


class Route:
    """
    Represents a single registered route.

    Stores the path pattern, allowed methods,
    and the handler function to call.
    """

    def __init__(self, path: str, handler, methods: list):
        self.path     = path
        self.handler  = handler
        self.methods  = [m.upper() for m in methods]
        self.pattern  = self._compile_pattern(path)
        self.params   = self._extract_param_names(path)

    def matches(self, path: str, method: str) -> bool:
        """Check if this route matches a path and method."""
        return (bool(self.pattern.match(path)) and
                method.upper() in self.methods)

    def extract_params(self, path: str) -> dict:
        """Extract dynamic parameters from the path."""
        match = self.pattern.match(path)
        if not match:
            return {}
        return dict(zip(self.params, match.groups()))

    def _compile_pattern(self, path: str) -> re.Pattern:
        """Convert path like /user/<name> to a regex."""
        pattern = re.sub(r"<([^>]+)>", r"([^/]+)", path)
        return re.compile(f"^{pattern}$")

    def _extract_param_names(self, path: str) -> list:
        """Extract parameter names from path like /user/<name>."""
        return re.findall(r"<([^>]+)>", path)

    def __repr__(self):
        return (f"Route({self.methods} {self.path})")


class Router:
    """
    Central routing system for NEKOVA web apps.

    Usage:
        router = Router()
        router.add("/", home_handler, methods=["GET"])
        response = router.handle(request)
    """

    def __init__(self):
        self.routes    = []
        self.not_found = not_found_response
        self.middlewares = []

    def add(self, path: str, handler,
            methods: list = None):
        """Register a new route."""
        if methods is None:
            methods = ["GET"]

        route = Route(path, handler, methods)
        self.routes.append(route)
        return route

    def handle(self, request: NEKOVARequest) -> NEKOVAResponse:
        """
        Find the matching route and call its handler.
        Returns a response object.
        """
        # Apply middlewares
        for middleware in self.middlewares:
            result = middleware(request)
            if result is not None:
                return result

        # Find matching route
        for route in self.routes:
            if route.matches(request.path, request.method):
                # Extract dynamic params and add to request
                params = route.extract_params(request.path)
                request.params.update(params)

                try:
                    result = route.handler(request)

                    # Auto-wrap string responses
                    if isinstance(result, str):
                        return text_response(result)
                    if isinstance(result, dict):
                        from nekova.web.response import json_response
                        return json_response(result)
                    if isinstance(result, NEKOVAResponse):
                        return result

                    return text_response(str(result))

                except Exception as e:
                    return error_response(
                        f"Handler error: {str(e)}",
                        status=500
                    )

        return not_found_response(request.path)

    def use(self, middleware):
        """Add a middleware function."""
        self.middlewares.append(middleware)

    def get_routes(self) -> list:
        """Return all registered routes."""
        return self.routes

    def __repr__(self):
        return f"Router({len(self.routes)} routes)"