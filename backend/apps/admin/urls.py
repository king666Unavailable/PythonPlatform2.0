from django.urls import path

from .navigation_views import admin_navigation_settings
from .views import audit_logs, class_members, classes, create_account, create_class, freeze_entity, frozen_items, import_accounts_confirm, import_accounts_preview, accounts, restore_frozen_entity, update_account, update_class


urlpatterns = [
    path("admin/accounts", accounts, name="admin-accounts"),
    path("admin/accounts/create", create_account, name="admin-account-create"),
    path("admin/accounts/import/preview", import_accounts_preview, name="admin-account-import-preview"),
    path("admin/accounts/import/confirm", import_accounts_confirm, name="admin-account-import-confirm"),
    path("admin/accounts/<str:role>/<str:username>", update_account, name="admin-account-update"),
    path("admin/classes", classes, name="admin-classes"),
    path("admin/frozen", frozen_items, name="admin-frozen-items"),
    path("admin/frozen/<str:entity_type>/<str:identifier>/restore", restore_frozen_entity, name="admin-frozen-restore"),
    path("admin/frozen/<str:entity_type>/<str:identifier>", freeze_entity, name="admin-freeze-entity"),
    path("admin/classes/create", create_class, name="admin-class-create"),
    path("admin/classes/<str:class_id>/members", class_members, name="admin-class-members"),
    path("admin/classes/<str:class_id>", update_class, name="admin-class-update"),
    path("admin/audit-logs", audit_logs, name="admin-audit-logs"),
    path("admin/navigation-settings", admin_navigation_settings, name="admin-navigation-settings"),
]
