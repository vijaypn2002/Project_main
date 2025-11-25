# backoffice/registry.py
from .client_admin import client_admin_site

from orders.models import Order, OrderItem, ReturnRequest, ReturnAttachment
from payments.models import Payment, PaymentEvent
from shipping.models import ShippingMethod, Shipment
from promotions.models import Coupon, CouponRedemption
from catalog.models import Category, Product, ProductVariant, Inventory, ProductImage
from cms.models import HomeBanner

# Prefer full-featured Payment admin if available; else readonly; else basic.
try:
    from payments.admin import PaymentAdmin, PaymentEventAdmin
    client_admin_site.register(Payment, PaymentAdmin)
    client_admin_site.register(PaymentEvent, PaymentEventAdmin)
except Exception:
    try:
        from payments.admin_readonly import PaymentROAdmin, PaymentEventROAdmin
        client_admin_site.register(Payment, PaymentROAdmin)
        client_admin_site.register(PaymentEvent, PaymentEventROAdmin)
    except Exception:
        client_admin_site.register(Payment)
        client_admin_site.register(PaymentEvent)

# Orders
client_admin_site.register(Order)
client_admin_site.register(OrderItem)
client_admin_site.register(ReturnRequest)
client_admin_site.register(ReturnAttachment)

# Shipping
client_admin_site.register(ShippingMethod)
client_admin_site.register(Shipment)

# Promotions
client_admin_site.register(Coupon)
client_admin_site.register(CouponRedemption)

# Catalog
client_admin_site.register(Category)
client_admin_site.register(Product)
client_admin_site.register(ProductVariant)
client_admin_site.register(Inventory)
client_admin_site.register(ProductImage)

# CMS
client_admin_site.register(HomeBanner)
