from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm, ProfileForm
from .models import Profile
from django.utils import timezone
from meals.models import MealPlan
# Create your views here.

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('create_profile')
    else:
        form = SignUpForm()
    return render(request, 'users/signup.html', {'form': form})

@login_required
def create_profile(request):
    if hasattr(request.user, 'profile'):
        return redirect('dashboard')
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            return redirect('dashboard')
    else:
        form = ProfileForm()
    return render(request, 'users/create_profile.html', {'form': form})

@login_required
def dashboard(request):
    profile = request.user.profile
    tdee = profile.calculate_tdee()

    # Get today's eaten calories
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1)
    
    today_meals = MealPlan.objects.filter(
        user=request.user,
        eaten=True,
        eaten_at__gte=today_start,
        eaten_at__lt=today_end
    )
    calories_consumed = sum(meal.calories for meal in today_meals)
    progress_percent = int((calories_consumed / tdee) * 100) if tdee > 0 else 0

    context = {
        'profile': profile,
        'tdee': tdee,
        'calories_consumed': calories_consumed,
        'progress_percent': min(progress_percent, 100),
    }
    return render(request, 'users/dashboard.html', context)