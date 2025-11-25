from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, BrandListView

app_name = "catalog"

router = DefaultRouter()
router.register(r"catalog/categories", CategoryViewSet, basename="category")
router.register(r"catalog/products", ProductViewSet, basename="product")

urlpatterns = router.urls + [
    path("catalog/brands/", BrandListView.as_view(), name="catalog-brands"),
]
