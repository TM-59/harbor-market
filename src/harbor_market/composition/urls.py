from django.urls import path

from harbor_market.presentation.views import health

urlpatterns = [path("health/", health, name="health")]
