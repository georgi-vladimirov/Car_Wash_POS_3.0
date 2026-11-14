from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def home(request: HttpRequest) -> HttpResponse:
    """Temporary start page; will be replaced by the wash panel."""
    return render(request, "core/home.html")
