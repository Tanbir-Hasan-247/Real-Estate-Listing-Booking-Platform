from django.contrib import messages

from django.shortcuts import get_object_or_404, redirect, render
from Real_Estate.views import User
from property.models import Property, PropertyImage, PropertyType, SavedProperty, TourBooking
from django.db.models import Q, Count
from .forms import PropertyForm, TourBookingForm
from django.contrib.auth import get_user_model

# Create your views here.

User = get_user_model()

def PropertyCreateView(request):
    form = PropertyForm()
    
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES)
        
        if form.is_valid():
            property = form.save(commit=False)
            property.agent = request.user
            property.status = 'available'
            print("Property created:", property)
            property.save()
            
            # Handle multiple images
            images = request.FILES.getlist('images')
            for image in images:
                PropertyImage.objects.create(property=property, image=image)
               
            return redirect('agent_dashboard')
        
    context = {
        'form': form,
    }
    return render(request, 'agent/add_property.html', context)

def PropertyEditView(request, pk):
    property = Property.objects.get(pk=pk, agent=request.user)
    form = PropertyForm(instance=property)
    
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property)
        
        if form.is_valid():
            property = form.save()
            
            # Handle new images
            images = request.FILES.getlist('images')
            for image in images:
                PropertyImage.objects.create(property=property, image=image)
                
            return redirect('agent_dashboard')
        
    context = {
        'form': form,
        'property': property,
    }
    return render(request, 'agent/add_property.html', context)

def PropertyDeleteView(request, pk):
    property = Property.objects.get(pk=pk, agent=request.user)
    property.delete()
    return redirect('agent_dashboard')

def AgentDashboardView(request):
    properties = (
            Property.objects
            .select_related('property_type', 'agent')
            .prefetch_related('images')
            .filter(agent=request.user)
        )
    
    tour_bookings = TourBooking.objects.select_related('property','buyer').filter(property__agent=request.user).order_by('-created_at')
    tour_bookings_count = tour_bookings.filter(status='Pending').count()
    
    propertie_count = properties.count()
    active_count = properties.filter(status='available').count()
    
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'available':
        properties = properties.filter(status='available')
        
    for property in properties:
        property.first_image = property.images.all()[0] if property.images.all() else None
    context = {
        'properties': properties,
        'property_count': propertie_count,
        'active_count': active_count,
        'tour_bookings': tour_bookings,
        'tour_bookings_count': tour_bookings_count,
    }
    return render(request, 'agent/dashboard.html', context)

def AgentPropertyListView(request):
    properties = (
            Property.objects
            .select_related('property_type', 'agent')
            .prefetch_related('images')
            .filter(agent=request.user)
        )
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    if search_query:
        properties = properties.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    if status_filter:
        properties = properties.filter(status=status_filter)

    for property in properties:
        property.first_image = property.images.all()[0] if property.images.all() else None
        
    context = {
        'properties': properties,
    }
    return render(request, 'agent/agent_properties.html', context)

# def PropertyDetailView(request, pk):
#     property = (
#         Property.objects
#         .select_related('property_type', 'agent')
#         .prefetch_related('images')
#         .get(pk=pk)
#     )
#     context = {
#         'property': property,
#     }
#     return render(request, 'property_detail.html', context)

def AgentProperty(request, pk):
    agent = get_object_or_404(User, pk=pk, role='agent')
    
    properties = (
            Property.objects
            .select_related('property_type', 'agent')
            .prefetch_related('images')
            .filter(agent=agent, status='available').order_by('-created_at')
        )
    
    for property in properties:
        property.first_image = property.images.all()[0] if property.images.all() else None
        
    context = {
        'agent': agent,
        'properties': properties,
    }
    return render(request, 'agent_profile.html', context)

def AgentTourRequestsView(request):
    bookings = TourBooking.objects.select_related('property', 'buyer').prefetch_related('property__images').filter(property__agent=request.user).order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        bookings = bookings.filter(status__iexact=status_filter)
        
    for booking in bookings:
        booking.property.first_image = booking.property.images.all()[0] if booking.property.images.all() else None

    context = {
        'bookings': bookings,
    }
    return render(request, 'agent/agent_tour_requests.html', context)

def UpdateTourStatusView(request, booking_id, new_status):
    if request.method == 'POST':
        booking = get_object_or_404(TourBooking, id=booking_id)
        
        if booking.property.agent != request.user and not request.user.is_superuser and request.user.role != 'admin':
            messages.error(request, "You do not have permission to update this booking.")
            return redirect('agent_tour_requests')

        valid_statuses = ['Pending', 'Confirmed', 'Cancelled', 'Completed']
        if new_status in valid_statuses:
            booking.status = new_status
            agent_msg = request.POST.get('agent_message', '')
            if agent_msg:
                booking.agent_message = agent_msg
            booking.save()
            messages.success(request, f"Tour status updated to {new_status} successfully.")
        else:
            messages.error(request, "Invalid status update.")
            
    return redirect('agent_tour_requests')

def BaseView(request):
    tour_requests = TourBooking.objects.select_related('property', 'buyer').prefetch_related('property__images').filter(property__agent=request.user)
    tour_requests_count = tour_requests.filter(status='Pending').count()
    context = {
        'tour_requests_count': tour_requests_count,
    }
    return render(request, 'agent/agent_base.html', context)

def AdminDashboardView(request):
    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('home')

    properties = (
        Property.objects
        .select_related('property_type', 'agent')
        .prefetch_related('images')
        .all()
        .order_by('-created_at') 
    )
    
    property_count = properties.count()
    active_count = properties.filter(status='available').count() 
    
    total_users = User.objects.count()
    total_agents = User.objects.filter(role='agent').count()
    
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'available':
        properties = properties.filter(status='available')
        
    for property in properties:
        property.first_image = property.images.all()[0] if property.images.all() else None

    tour_bookings = TourBooking.objects.select_related('property', 'buyer','property__agent','property__property_type').prefetch_related('property__images').all().order_by('-created_at')[:10]
    pending_tours_count = TourBooking.objects.filter(status='Pending').count()

    context = {
        'properties': properties[:10], 
        'property_count': property_count,
        'active_count': active_count,
        'total_users': total_users,
        'total_agents': total_agents,
        'tour_bookings': tour_bookings,
        'pending_tours_count': pending_tours_count,
    }
    return render(request, 'admin/admin_dashboard.html', context) 

def AdminPropertyListView(request):
    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('home')

    properties = (
        Property.objects
        .select_related('property_type', 'agent')
        .prefetch_related('images')
        .all()
        .order_by('-created_at') 
    )
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    if search_query:
        properties = properties.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    if status_filter:
        properties = properties.filter(status=status_filter)

    for property in properties:
        property.first_image = property.images.all()[0] if property.images.all() else None

    context = {
        'properties': properties, 
    }
    return render(request, 'admin/all_properties.html', context)

def AdminPropertyTypeListView(request):
    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('home')

    property_types = PropertyType.objects.prefetch_related('properties').annotate(property_count=Count('properties')).order_by('-property_count')
    
    context = {
        'property_types': property_types,
    }
    return render(request, 'admin/property_types.html', context)


def AdminUserListView(request):
    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('home')

    users = User.objects.all().order_by('-date_joined')
    
    search_query = request.GET.get('search')
    role_filter = request.GET.get('role')
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query)
        )
        
    if role_filter:
        users = users.filter(role=role_filter)

    context = {
        'users': users,
    }
    return render(request, 'admin/admin_user_list.html', context)



def AdminAgentListView(request):
    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('home')

    agents = User.objects.filter(role='agent').order_by('-date_joined')

    context = {
        'agents': agents,
    }
    return render(request, 'admin/admin_agent_list.html', context)


def AdminTourRequestsView(request):
    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('home')

    bookings = TourBooking.objects.select_related('property__agent', 'buyer').prefetch_related('property__images').all().order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        bookings = bookings.filter(status__iexact=status_filter)
        
    if bookings:
        for booking in bookings:
            booking.property.first_image = booking.property.images.all()[0] if booking.property.images.all() else None

    context = {
        'bookings': bookings,
    }
    return render(request, 'admin/admin_tour_requests.html', context)


def PropertyDetailView(request, id):
    property_obj = get_object_or_404(Property.objects.prefetch_related('images'), id=id)
    
    is_saved = False
    if request.user.is_authenticated:
        is_saved = SavedProperty.objects.filter(user=request.user, property=property_obj).exists()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "You need to log in to book a tour.")
            return redirect('login')
            
        if request.user == property_obj.agent:
            messages.error(request, "You cannot book a tour for your own property!")
            return redirect('property_detail', id=id)

        form = TourBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.property = property_obj
            booking.buyer = request.user
            booking.save()
            messages.success(request, "Tour requested successfully! The agent will contact you soon.")
            return redirect('property_detail', id=id)
    else:
        # GET রিকোয়েস্টের জন্য (এখানে else দেওয়াটা জরুরি)
        form = TourBookingForm()

    context = {
        'property': property_obj,
        'form': form,
        'is_saved': is_saved,
    }
    return render(request, 'property_detail.html', context)


def ToggleSavePropertyView(request, id):
    property_obj = get_object_or_404(Property, id=id)
    saved_item = SavedProperty.objects.filter(user=request.user, property=property_obj).first()

    if saved_item:
        saved_item.delete()
        # messages.success(request, "Removed from your saved properties.")
    else:
        SavedProperty.objects.create(user=request.user, property=property_obj)
        # messages.success(request, "Property saved to your wishlist!")

    return redirect(request.META.get('HTTP_REFERER', 'home'))

def SavedPropertiesView(request):
    saved_items = SavedProperty.objects.filter(user=request.user).select_related('property')
    
    context = {
        'saved_items': saved_items,
    }
    return render(request, 'saved_properties.html', context)