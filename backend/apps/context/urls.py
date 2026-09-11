from django.urls import path

from .navigation_views import navigation
from .views import class_context, current_class

urlpatterns = [
    path("context/classes", class_context, name="class-context"),
    path("context/classes/current", current_class, name="current-class"),
    path("navigation", navigation, name="navigation"),
]
