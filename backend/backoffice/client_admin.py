# backoffice/client_admin.py
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class ClientAdminSite(AdminSite):
    site_header = _("MyShop Backoffice")
    site_title = _("MyShop Backoffice")
    index_title = _("Welcome")

client_admin_site = ClientAdminSite(name="client_admin")
