import re
from fastapi import Request, Response
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.base import DispatchFunction
from starlette.types import ASGIApp
from typing import Optional
from .core import Babel, _context_var, _context_var_pgettext, get_language_to_use, initialize_babel_of_request
from .properties import RootConfigs
from pathlib import Path




class BabelMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        babel_configs: RootConfigs,
        jinja2_templates: Optional[Jinja2Templates] = None,
        dispatch: Optional[DispatchFunction] = None,
    ) -> None:
        super().__init__(app, dispatch)
        self.babel_configs = babel_configs
        self.jinja2_templates = jinja2_templates

    def get_language(self, lang_code):
        return get_language_to_use(self.babel_configs, lang_code)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """dispatch function

        Args:
            request (Request): ...
            call_next (RequestResponseEndpoint): ...

        Returns:
            Response: ...
        """
        lang_code: Optional[str] = request.headers.get("Accept-Language", None)
        real_lang_code = self.get_language(lang_code)
        initialize_babel_of_request(request, self.babel_configs, real_lang_code, self.jinja2_templates)
        response: Response = await call_next(request)
        return response
