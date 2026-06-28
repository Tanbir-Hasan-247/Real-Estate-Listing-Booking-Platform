from django.shortcuts import render
from django.views import View
from django.views.generic import ListView
from property.models import Property
from django.db.models import Q, Count
from django.contrib.auth import get_user_model

User = get_user_model()

# def HomeView(request):
#     properties = (
#         Property.objects
#         .select_related('property_type', 'agent')
#         .prefetch_related('images')
#         .filter(status='available')
#         .order_by('-created_at')[:3]
#     )

#     for property in properties:
#         property.first_image = property.images.all()[0] if property.images.all() else None

#     context = {
#         'properties': properties,
#     }

#     return render(request, 'home.html', context)

class HomeView(View):
    def get(self, request):
        properties = (
            Property.objects
            .select_related('property_type', 'agent')
            .prefetch_related('images')
            .filter(status='available')
            .order_by('-created_at')[:3]
        )

        for property in properties:
            property.first_image = property.images.all()[0] if property.images.all() else None

        context = {
            'properties': properties,
        }

        return render(request, 'home.html', context)


# def PropertyListView(request):
#     properties = (
#         Property.objects
#         .select_related('property_type', 'agent')
#         .prefetch_related('images')
#         .filter(status='available')
#     )

#     search_query = request.GET.get('search')
#     listing_type = request.GET.get('listing_type')
#     property_type = request.GET.get('property_type')
#     bedrooms = request.GET.get('bedrooms')
#     min_price = request.GET.get('min_price')
#     max_price = request.GET.get('max_price')
    
#     sort_by = request.GET.get('sort')

#     if search_query:
#         properties = properties.filter(
#             Q(title__icontains=search_query) |
#             Q(location__icontains=search_query) |
#             Q(city__icontains=search_query)
#         )
#     if listing_type:
#         properties = properties.filter(listing_type=listing_type)
#     if property_type:
#         properties = properties.filter(property_type__name=property_type)
#     if bedrooms:
#         properties = properties.filter(bedrooms__gte=bedrooms)
#     if min_price:
#         properties = properties.filter(price__gte=min_price)
#     if max_price:
#         properties = properties.filter(price__lte=max_price)

#     if sort_by == 'price_asc':
#         properties = properties.order_by('price')       
#     elif sort_by == 'price_desc':
#         properties = properties.order_by('-price')       
#     else:
#         properties = properties.order_by('-created_at')  

#     for property in properties:
#         property.first_image = property.images.all()[0] if property.images.all() else None

#     context = {
#         'properties': properties,
#     }
#     return render(request, 'property_list.html', context)

class PropertyListView(ListView):
    model = Property
    template_name = 'property_list.html'
    context_object_name = 'properties'

    def get_queryset(self):
        properties = (
            Property.objects
            .select_related('property_type', 'agent')
            .prefetch_related('images')
            .filter(status='available')
        )
        search_query = self.request.GET.get('search')
        listing_type = self.request.GET.get('listing_type')
        property_type = self.request.GET.get('property_type')
        bedrooms = self.request.GET.get('bedrooms')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        sort_by = self.request.GET.get('sort')
        
        if search_query:
            properties = properties.filter(
                Q(title__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(city__icontains=search_query)
            )
        if listing_type:
            properties = properties.filter(listing_type=listing_type)
        if property_type:
            properties = properties.filter(property_type__name=property_type)
        if bedrooms:
            properties = properties.filter(bedrooms__gte=bedrooms)
        if min_price:
            properties = properties.filter(price__gte=min_price)
        if max_price:
            properties = properties.filter(price__lte=max_price)

        if sort_by == 'price_asc':
            properties = properties.order_by('price')
        elif sort_by == 'price_desc':
            properties = properties.order_by('-price')
        else:
            properties = properties.order_by('-created_at')
            
        for property in properties:
            property.first_image = property.images.all()[0] if property.images.all() else None
            
        return properties

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

# def AgentListView(request):
#     agents = User.objects.filter(role=User.AGENT).annotate(
#         property_count=Count('property', filter=Q(property__status='available'))
#     ).order_by('-property_count') 

#     search_query = request.GET.get('search')
#     if search_query:
#         agents = agents.filter(
#             Q(first_name__icontains=search_query) |
#             Q(last_name__icontains=search_query) |
#             Q(username__icontains=search_query)
#         )

#     context = {
#         'agents': agents,
#     }
#     return render(request, 'agent/agent_list.html', context)

class AgentListView(ListView):
    model = User
    template_name = 'agent/agent_list.html'
    context_object_name = 'agents'

    def get_queryset(self):
        agents = User.objects.filter(role=User.AGENT).annotate(
            property_count=Count('property', filter=Q(property__status='available'))
        ).order_by('-property_count')

        search_query = self.request.GET.get('search')
        if search_query:
            agents = agents.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(username__icontains=search_query)
            )
        return agents