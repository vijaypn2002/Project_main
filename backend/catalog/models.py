from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify


def _unique_slug(instance, base_value: str, slug_field: str = "slug", max_len: int = 200):
    """
    Generate a de-duplicated slug like 'name', 'name-2', ... within the model.
    Respects the field's max_length.
    """
    model = instance.__class__
    base = slugify(base_value)[: max_len].strip("-") or "item"
    slug = base
    i = 2
    while model.objects.filter(**{slug_field: slug}).exclude(pk=getattr(instance, "pk", None)).exists():
        suffix = f"-{i}"
        slug = (base[: max_len - len(suffix)] + suffix).strip("-")
        i += 1
    return slug


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True, db_index=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        related_name="children", on_delete=models.CASCADE
    )

    # --- Drive the homepage/category belt from admin ---
    show_in_nav = models.BooleanField(default=False, help_text="Show in the top category belt")
    nav_label = models.CharField(
        max_length=60, blank=True,
        help_text="Optional short label to display instead of name"
    )
    nav_order = models.PositiveIntegerField(default=0, help_text="Smaller comes first")
    icon = models.ImageField(
        upload_to="category-icons/", blank=True,
        help_text="Small square icon used in the top belt"
    )

    class Meta:
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=["show_in_nav", "nav_order"]),
            models.Index(fields=["parent"]),
        ]
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(self, self.name, max_len=140)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def display_label(self) -> str:
        """Use nav_label in belts when provided, else fall back to name."""
        return self.nav_label.strip() or self.name


class Product(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DRAFT = "draft", "Draft"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True, db_index=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.PROTECT)
    brand = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["brand"]),
            models.Index(fields=["category", "status"]),
        ]
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(self, self.name, max_len=200)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    sku = models.CharField(max_length=64, unique=True, db_index=True)
    attributes = models.JSONField(default=dict, blank=True)
    price_mrp = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    price_sale = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])

    class Meta:
        indexes = [
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"{self.product.name} [{self.sku}]"

    def clean(self):
        super().clean()
        if self.price_sale is not None and self.price_sale > self.price_mrp:
            raise ValidationError({"price_sale": "Sale price cannot exceed MRP."})

    @property
    def price_effective(self):
        return self.price_sale if self.price_sale is not None else self.price_mrp


class Inventory(models.Model):
    class Backorder(models.TextChoices):
        BLOCK = "block", "Block"
        ALLOW = "allow", "Allow"
        NOTIFY = "notify", "Notify"  # NEW

    variant = models.OneToOneField(ProductVariant, related_name="inventory", on_delete=models.CASCADE)
    qty_available = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    backorder_policy = models.CharField(max_length=30, choices=Backorder.choices, default=Backorder.BLOCK)
    expected_restock_date = models.DateField(null=True, blank=True)  # NEW (optional ETA)

    def __str__(self):
        return f"{self.variant.sku} stock={self.qty_available}"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=180)  # REQUIRED for a11y/SEO
    is_primary = models.BooleanField(default=False)
    sort = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]
        constraints = [
            # Enforce only one primary image per product
            models.UniqueConstraint(
                fields=["product"], condition=Q(is_primary=True), name="uq_product_single_primary_image"
            ),
        ]
        indexes = [
            models.Index(fields=["product", "is_primary", "sort"]),
        ]

    def save(self, *args, **kwargs):
        # Require alt text at runtime too (extra safety if admin bypasses form validation)
        if not (self.alt_text or "").strip():
            raise ValidationError({"alt_text": "Alt text is required for product images."})
        # If this becomes primary, demote others
        if self.is_primary and self.product_id:
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image({self.product_id})#{self.pk} primary={self.is_primary}"
