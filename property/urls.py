from django.urls import path
from . import views
urlpatterns = [
    path('agent/add-property/', views.PropertyCreateView, name='add_property'),
    path('agent/property/<int:pk>/edit/', views.PropertyEditView, name='edit_property'),
    path('agent/property/<int:pk>/delete/', views.PropertyDeleteView, name='delete_property'),
    path('agent/dashboard/', views.AgentDashboardView, name='agent_dashboard'),
    path('agent/properties/', views.AgentPropertyListView, name='agent_property_list'),
    path('agent/tour-requests/', views.AgentTourRequestsView, name='agent_tour_requests'),
    path('agent/tour-requests/update/<int:booking_id>/<str:new_status>/', views.UpdateTourStatusView, name='update_tour_status'),
    # path('property/<int:id>/', views.PropertyDetailView, name='property_detail'),
    path('properties/agent/<int:pk>/', views.AgentProperty, name='properties_by_agent'),
    path('admin-panel/dashboard/', views.AdminDashboardView, name='admin_dashboard'),
    path('admin-panel/properties/', views.AdminPropertyListView, name='admin_property_list'),
    path("admin-panel/property-type/", views.AdminPropertyTypeListView, name='admin_property_types'),
    path("admin-panel/all-users/", views.AdminUserListView, name='admin_user_list'),
    path("admin-panel/agents/", views.AdminAgentListView, name='admin_agent_list'),
    path("admin-panel/tour-requests/", views.AdminTourRequestsView, name='admin_tour_requests'),
    path("property/<int:id>/", views.PropertyDetailView, name='property_detail'),
    path('property/<int:id>/toggle-save/', views.ToggleSavePropertyView, name='save_property'),
    path('saved-properties/', views.SavedPropertiesView, name='saved_properties'),
]