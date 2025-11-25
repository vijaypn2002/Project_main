from django.urls import path
from .views import ReportsSummaryView, TopProductsView

app_name = "reports"

urlpatterns = [
    path("reports/summary", ReportsSummaryView.as_view(), name="reports-summary"),
    path("reports/top-products", TopProductsView.as_view(), name="reports-top-products"),
]
