from pyexpat.errors import messages

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model, login, logout
from .forms import CustomUserCreationForm, LoginForm
from django.contrib.auth.tokens import default_token_generator
# Create your views here.
User = get_user_model()

def UserRegistrationView(request):
    form = CustomUserCreationForm()
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        
        if form.is_valid():
            form.save()
            return redirect('login')
        
    context = {'form': form}
    return render(request, 'users/register.html', context)


def UserLoginView(request):
    form = LoginForm()
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.role == 'agent':
                return redirect('agent_dashboard')
            if user.role == 'admin' or user.is_superuser:
                return redirect('admin_dashboard')
            return redirect('home')
        
    context = {'form': form}
    return render(request, 'users/login.html', context)

def UserLogoutView(request):
    logout(request)
    return redirect('home')

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