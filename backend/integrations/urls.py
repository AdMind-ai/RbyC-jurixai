from django.urls import path, include
from .views import *

app_name = "integrations"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("v1/", include("integrations.v1.urls")),
]