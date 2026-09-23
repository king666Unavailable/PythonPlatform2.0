"""Root URL configuration."""

from pathlib import Path

from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("api/v1/", include("api.v1.urls")),
]


def _serve_index(request, **kwargs):
    # index.html must never be cached: it references hashed asset bundles that
    # change on every rebuild, and classroom browsers would otherwise pin the
    # previous build until a manual hard refresh.
    response = serve(request, "index.html", document_root=kwargs.get("document_root", FRONTEND_DIST))
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


# 单端口部署：同端口托管前端构建产物（frontend/dist），/api 之外的路径回落到 SPA 入口。
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if settings.SERVE_FRONTEND_DIST and FRONTEND_DIST.is_dir():
    urlpatterns += [
        re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": FRONTEND_DIST / "assets"}),
        re_path(r"^(?!api/|assets/).*$", _serve_index),
    ]
