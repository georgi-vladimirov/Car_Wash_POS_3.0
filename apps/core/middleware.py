from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import resolve_url
from django_htmx.http import HttpResponseClientRedirect


class HtmxLoginRedirectMiddleware:
    """Turn login redirects of htmx requests into a full-page redirect.

    Without this, htmx follows the 302 silently and swaps the login page
    into the target fragment (e.g. inside a table) after the session expires.
    Must be placed below django_htmx.middleware.HtmxMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (
            request.htmx
            and response.status_code == 302
            and not request.user.is_authenticated
            and urlparse(response["Location"]).path == resolve_url(settings.LOGIN_URL)
        ):
            # Return to the page the user was on, not to the fragment URL
            next_url = request.htmx.current_url_abs_path or "/"
            login_url = redirect_to_login(next_url)["Location"]
            return HttpResponseClientRedirect(login_url)

        return response
