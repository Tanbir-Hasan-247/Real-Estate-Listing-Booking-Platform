from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from Real_Estate import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.HomeView.as_view(), name="home"),
    path("properties/", views.PropertyListView.as_view(), name="property_list"),
    path("agents/", views.AgentListView.as_view(), name="agent_list"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("", include("users.urls")),
    path("", include("property.urls")),
]

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
