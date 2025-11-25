from django.db import models
from django.core.exceptions import ValidationError


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class HomeBanner(TimeStamped):
    image = models.ImageField(upload_to="banners/")
    title = models.CharField(max_length=120, blank=True)
    alt = models.CharField(max_length=160)  # a11y: required
    href = models.CharField(max_length=300, blank=True, help_text="Optional click-through URL")
    sort = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "id"]
        indexes = [models.Index(fields=["is_active", "sort"])]
        verbose_name = "Home Banner"
        verbose_name_plural = "Home Banners"

    def clean(self):
        super().clean()
        if not (self.alt or "").strip():
            raise ValidationError({"alt": "Alt text is required for accessibility."})

    def __str__(self):
        return self.title or f"Banner #{self.pk}"


class HomeRail(TimeStamped):
    """
    A simple, CMS-driven product rail header for the homepage.
    We return title + optional 'view all' link; items are optional
    (frontend can still render an empty rail if you want the header only).

    If you later want the backend to also hydrate items, you can add fields
    like `source_path` and `params_json` and query your catalog here.
    """
    title = models.CharField(max_length=120)
    view_all = models.CharField(
        max_length=300,
        blank=True,
        help_text="Frontend URL to a filtered listing (e.g. /search?price_max=999)."
    )
    # future-ready placeholders (not used yet)
    source_path = models.CharField(
        max_length=300, blank=True,
        help_text="(Optional) API path to fetch items server-side later, e.g. /catalog/products/"
    )
    params_json = models.JSONField(
        default=dict, blank=True,
        help_text="(Optional) Query params for server-side fetching later."
    )

    sort = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "id"]
        indexes = [models.Index(fields=["is_active", "sort"])]
        verbose_name = "Home Rail"
        verbose_name_plural = "Home Rails"

    def __str__(self):
        return self.title
