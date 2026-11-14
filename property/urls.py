from django.urls import path

from . import views

urlpatterns = [
    # Agent & Admin Property Operations
    path("agent/add-property/", views.PropertyCreateView, name="add_property"),
    path("agent/property/<int:pk>/edit/", views.PropertyEditView, name="edit_property"),
    path("agent/property/<int:pk>/delete/", views.PropertyDeleteView, name="delete_property"),
    path("agent/property-image/<int:pk>/delete/", views.DeletePropertyImageView, name="delete_property_image"),
    path("agent/dashboard/", views.AgentDashboardView.as_view(), name="agent_dashboard"),
    path("agent/properties/", views.AgentPropertyListView, name="agent_property_list"),
    path("agent/tour-requests/", views.AgentTourRequestsView, name="agent_tour_requests"),
    path(
        "agent/tour-requests/update/<int:booking_id>/<str:new_status>/",
        views.UpdateTourStatusView,
        name="update_tour_status",
    ),
    # Public Agent Showcase & Detail
    path("properties/agent/<int:pk>/", views.AgentProperty, name="properties_by_agent"),
    path("properties/compare/", views.ComparePropertiesView, name="compare_properties"),
    path("property/<int:id>/", views.PropertyDetailView.as_view(), name="property_detail"),
    path("property/<int:id>/review/", views.SubmitPropertyReviewView, name="submit_property_review"),
    path("property/<int:id>/toggle-save/", views.ToggleSavePropertyView, name="save_property"),
    path("saved-properties/", views.SavedPropertiesView, name="saved_properties"),
    path("my-tours/", views.MyTourBookingsView, name="my_tours"),
    path("my-tours/cancel/<int:booking_id>/", views.CancelMyTourView, name="cancel_my_tour"),
    path("notifications/", views.NotificationListView, name="notifications"),
    path("notifications/<int:pk>/read/", views.MarkNotificationReadView, name="mark_notification_read"),
    path("notifications/read-all/", views.MarkAllNotificationsReadView, name="mark_all_notifications_read"),
    # Admin Portal
    path("admin-panel/dashboard/", views.AdminDashboardView, name="admin_dashboard"),
    path("admin-panel/properties/", views.AdminPropertyListView, name="admin_property_list"),
    path("admin-panel/property-type/", views.AdminPropertyTypeListView, name="admin_property_types"),
    path(
        "admin-panel/property-type/<int:pk>/delete/",
        views.AdminDeletePropertyTypeView,
        name="admin_delete_property_type",
    ),
    path("admin-panel/all-users/", views.AdminUserListView, name="admin_user_list"),
    path("admin-panel/users/<int:pk>/role/", views.AdminUpdateUserRoleView, name="admin_update_user_role"),
    path("admin-panel/users/<int:pk>/toggle/", views.AdminToggleUserActiveView, name="admin_toggle_user_active"),
    path("admin-panel/users/<int:pk>/delete/", views.AdminDeleteUserView, name="admin_delete_user"),
    path("admin-panel/agents/", views.AdminAgentListView, name="admin_agent_list"),
    path("admin-panel/tour-requests/", views.AdminTourRequestsView, name="admin_tour_requests"),
    path("admin-panel/inquiries/", views.AdminInquiryListView, name="admin_inquiries"),
    path("admin-panel/inquiries/<int:pk>/toggle/", views.AdminToggleInquiryView, name="admin_toggle_inquiry"),
    path("admin-panel/export-report/", views.AdminExportReportView, name="admin_export_report"),
]
