from pyexpat.errors import messages

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model, login, logout
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm, LoginForm
from django.contrib.auth.tokens import default_token_generator
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import UserPassesTestMixin
# Create your views here.
User = get_user_model()

# def UserRegistrationView(request):
#     form = CustomUserCreationForm()
    
#     if request.method == 'POST':
#         form = CustomUserCreationForm(request.POST, request.FILES)
        
#         if form.is_valid():
#             form.save()
#             return redirect('login')
        
#     context = {'form': form}
#     return render(request, 'users/register.html', context)

class UserRegistrationView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('login')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            user = request.user
            if user.role == 'agent':
                return redirect('agent_dashboard')
            if user.role == 'admin' or user.is_superuser:
                return redirect('admin_dashboard')
            return redirect('home')
        
        return super().dispatch(request, *args, **kwargs)

# def UserLoginView(request):
#     form = LoginForm()
    
#     if request.method == 'POST':
#         form = LoginForm(request, data=request.POST)
        
#         if form.is_valid():
#             user = form.get_user()
#             login(request, user)
#             if user.role == 'agent':
#                 return redirect('agent_dashboard')
#             if user.role == 'admin' or user.is_superuser:
#                 return redirect('admin_dashboard')
#             return redirect('home')
        
#     context = {'form': form}
#     return render(request, 'users/login.html', context)

class UserLoginView(LoginView):
    form_class = LoginForm
    template_name = 'users/login.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            user = request.user
            if user.role == 'agent':
                return redirect('agent_dashboard')
            if user.role == 'admin' or user.is_superuser:
                return redirect('admin_dashboard')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        user = self.request.user
        if user.role == 'agent':
            return reverse_lazy('agent_dashboard')
        if user.role == 'admin' or user.is_superuser:
            return reverse_lazy('admin_dashboard')
        return reverse_lazy('home')

# def UserLogoutView(request):
#     logout(request)
#     return redirect('home')

class UserLogoutView(LogoutView):
    next_page = 'home'

def ProfileView(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.phone_number = request.POST.get('phone_number')
        user.bio = request.POST.get('bio')
        
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
            
        user.save()
        # messages.success(request, 'Profile updated successfully!')
        return redirect('profile') # এই পেজেই ফিরে আসবে
        
    return render(request, 'user_profile.html')

def activate_user(request, user_id, token):
    try:
        user = User.objects.get(id=user_id)
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return redirect('login')
        else:
            return HttpResponse('Invalid Id or token')

    except User.DoesNotExist:
        return HttpResponse('User not found')