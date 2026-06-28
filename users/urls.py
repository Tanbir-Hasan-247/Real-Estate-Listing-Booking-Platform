from django.urls import path
from . import views

urlpatterns = [
    # path('register/', views.UserRegistrationView, name='register'),
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    # path('login/', views.UserLoginView, name='login'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    # path('logout/', views.UserLogoutView, name='logout'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView, name='profile'),
    path('activate/<int:user_id>/<str:token>/', views.activate_user, name='activate_user'),
]