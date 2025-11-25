from django.urls import path
from .views import HomeContentView

app_name = "cms"

urlpatterns = [
    path("content/home", HomeContentView.as_view(), name="home-content"),
    path("cms/home", HomeContentView.as_view(), name="home-content-alias"),
]
