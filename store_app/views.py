from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import Product, Customer

def home(request):
  products = Product.objects.all()
  return render(request,"home.html", {'products': products})

def search(request):
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )
    else:
        products = Product.objects.all()
    
    return render(request, 'home.html', {
        'products': products,
        'query': query
    })

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Find user by email
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Successfully logged in!')
                return redirect('home')
            else:
                messages.error(request, 'Invalid email or password.')
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'login.html')

def signup_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Check if passwords match
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'signup.html')
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'signup.html')
        
        # Create user
        username = email.split('@')[0]  # Use email prefix as username
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create customer profile
        Customer.objects.create(
            user=user,
            phone_number=phone_number
        )
        
        messages.success(request, 'Account created successfully! Please log in.')
        return redirect('login')
    
    return render(request, 'signup.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')
