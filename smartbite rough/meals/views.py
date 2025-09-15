import csv
import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from .models import MealPlan
from users.models import Profile
import requests

# meals/views.py

import csv
import json
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import MealPlan
from users.models import Profile
import requests
from django.conf import settings
from django.http import JsonResponse


@login_required
def generate_meal_plan(request):
    profile = request.user.profile
    calorie_target = profile.calculate_tdee()
    goal = profile.goal

    # Adjust daily calories per goal
    if goal == 'lose':
        daily_calories = int(calorie_target * 0.85)  # 15% deficit
    elif goal == 'gain':
        daily_calories = int(calorie_target * 1.15)  # 15% surplus
    else:
        daily_calories = calorie_target

    # Target per meal (4 meals/day)
    target_calories_per_meal = daily_calories // 4

    # Build diet & intolerance filters from profile
    diet = ""
    intolerances = ""

    if profile.health_issues:
        issues = profile.health_issues.lower()
        if "diabetes" in issues:
            diet = "low glycemic"
        if "gluten" in issues:
            intolerances = "gluten"
        if "lactose" in issues:
            if intolerances:
                intolerances += ",dairy"
            else:
                intolerances = "dairy"

    # API URL
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        'apiKey': settings.SPOONACULAR_API_KEY,
        'number': 28,  # 7 days x 4 meals
        'minCalories': max(100, target_calories_per_meal - 100),
        'maxCalories': target_calories_per_meal + 100,
        'diet': diet,
        'intolerances': intolerances,
        'addRecipeInformation': True,
        'fillIngredients': True,
        'sort': 'calories',
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        recipes = data.get('results', [])
    except Exception as e:
        print("API Error:", e)
        recipes = []  # fallback to mock if API fails

    # Clear old plan
    MealPlan.objects.filter(user=request.user).delete()

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    meal_types = ["Breakfast", "Lunch", "Dinner", "Snack"]

    if not recipes:
        # Fallback mock meals
        recipes = [
            {"title": "Oatmeal with Berries", "calories": target_calories_per_meal, "protein": 10, "carbs": 50, "fat": 5},
            {"title": "Grilled Chicken Salad", "calories": target_calories_per_meal, "protein": 30, "carbs": 20, "fat": 10},
            {"title": "Salmon with Quinoa", "calories": target_calories_per_meal, "protein": 35, "carbs": 40, "fat": 15},
            {"title": "Greek Yogurt & Nuts", "calories": target_calories_per_meal, "protein": 15, "carbs": 20, "fat": 10},
        ]

    recipe_index = 0
    for day in days:
        for meal_type in meal_types:
            if recipe_index >= len(recipes):
                break

            recipe = recipes[recipe_index]
            recipe_index += 1

            # Extract nutrition (fallback if not available)
            nutrition = recipe.get('nutrition', {}).get('nutrients', [])
            protein = carbs = fat = 0

            for n in nutrition:
                if n['name'] == 'Protein':
                    protein = round(n['amount'])
                elif n['name'] == 'Carbohydrates':
                    carbs = round(n['amount'])
                elif n['name'] == 'Fat':
                    fat = round(n['amount'])

            # Create meal plan entry
            MealPlan.objects.create(
                user=request.user,
                day=day,
                meal_type=meal_type,
                meal_name=recipe['title'],
                calories=recipe.get('calories', target_calories_per_meal),
                protein=protein,
                carbs=carbs,
                fats=fat,
                image_url=recipe.get('image', ''),
            )

    return redirect('meal_plan')
@login_required
def meal_plan_view(request):
    meals = MealPlan.objects.filter(user=request.user).order_by('id')[:28]  # 7 days x 4 meals
    grouped_meals = {}
    for meal in meals:
        if meal.day not in grouped_meals:
            grouped_meals[meal.day] = []
        grouped_meals[meal.day].append(meal)

    return render(request, 'meals/meal_plan.html', {'grouped_meals': grouped_meals})

@login_required
def grocery_list(request):
    # Only include meals that are in the plan (ignore uneaten or unassigned ones? Optional)
    meals = MealPlan.objects.filter(user=request.user)
    shopping_list = []

    for meal in meals:
        if not meal.image_url:
            continue  # Skip if no API data

        try:
            # Fetch ingredients using recipe title or ID (enhance later with caching)
            url = "https://api.spoonacular.com/recipes/complexSearch"
            params = {
                'apiKey': settings.SPOONACULAR_API_KEY,
                'query': meal.meal_name,
                'number': 1,
                'addRecipeInformation': True,
            }
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    recipe = data['results'][0]
                    ingredients = [ing['original'] for ing in recipe.get('extendedIngredients', [])]
                    shopping_list.extend(ingredients)
        except:
            pass

    # Fallback mock if API fails
    if not shopping_list:
        generic_ingredients = {
            "Oatmeal with Berries": ["Oats (1 cup)", "Mixed berries (1/2 cup)", "Almond milk (1 cup)"],
            "Grilled Chicken Salad": ["Chicken breast (150g)", "Mixed greens (2 cups)", "Cherry tomatoes (1/2 cup)", "Olive oil (1 tbsp)"],
            "Salmon with Quinoa": ["Salmon fillet (150g)", "Quinoa (1/2 cup cooked)", "Steamed broccoli (1 cup)", "Lemon juice (1 tbsp)"],
            "Greek Yogurt & Nuts": ["Greek yogurt (1 cup)", "Mixed nuts (1/4 cup)", "Honey (1 tsp)"],
        }
        for meal in meals:
            ingredients = generic_ingredients.get(meal.meal_name, [f"Ingredient for {meal.meal_name}"])
            shopping_list.extend(ingredients)

    shopping_list = sorted(list(set(shopping_list)))

    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="grocery_list.csv"'
        writer = csv.writer(response)
        writer.writerow(['Grocery Item'])
        for item in shopping_list:
            writer.writerow([item])
        return response

    return render(request, 'meals/grocery_list.html', {'shopping_list': shopping_list})

from django.db.models import Sum, Count
from datetime import timedelta

@login_required
def progress_view(request):
    # Last 7 days of eaten meals
    seven_days_ago = timezone.now() - timedelta(days=7)
    meals = MealPlan.objects.filter(
        user=request.user,
        eaten=True,
        eaten_at__gte=seven_days_ago
    ).order_by('eaten_at')

    # Group by date
    daily_data = {}
    for meal in meals:
        date_str = meal.eaten_at.strftime("%Y-%m-%d")
        if date_str not in daily_data:
            daily_data[date_str] = {'calories': 0, 'meals': 0}
        daily_data[date_str]['calories'] += meal.calories
        daily_data[date_str]['meals'] += 1

    dates = list(daily_data.keys())
    calories = [daily_data[d]['calories'] for d in dates]
    meal_counts = [daily_data[d]['meals'] for d in dates]

    # Weekly summary
    total_calories = sum(calories)
    total_meals = sum(meal_counts)
    avg_daily_calories = total_calories // len(dates) if dates else 0

    context = {
        'dates_json': json.dumps(dates),
        'calories_json': json.dumps(calories),
        'meal_counts_json': json.dumps(meal_counts),
        'total_calories': total_calories,
        'total_meals': total_meals,
        'avg_daily_calories': avg_daily_calories,
        'days_tracked': len(dates),
    }
    return render(request, 'meals/progress.html', context)

@login_required
def replace_meal(request, meal_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        old_meal = MealPlan.objects.get(id=meal_id, user=request.user)
        profile = request.user.profile
        calorie_target = profile.calculate_tdee()

        # Get new meal from API (similar to generate logic)
        target_calories = old_meal.calories
        diet = ""
        intolerances = ""

        if profile.health_issues:
            issues = profile.health_issues.lower()
            if "diabetes" in issues:
                diet = "low glycemic"
            if "gluten" in issues:
                intolerances = "gluten"

        url = "https://api.spoonacular.com/recipes/complexSearch"
        params = {
            'apiKey': settings.SPOONACULAR_API_KEY,
            'number': 1,
            'minCalories': max(100, target_calories - 100),
            'maxCalories': target_calories + 100,
            'diet': diet,
            'intolerances': intolerances,
            'addRecipeInformation': True,
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        recipes = data.get('results', [])

        if not recipes:
            return JsonResponse({'error': 'No replacement found'}, status=404)

        recipe = recipes[0]
        nutrition = recipe.get('nutrition', {}).get('nutrients', [])
        protein = carbs = fat = 0
        for n in nutrition:
            if n['name'] == 'Protein': protein = round(n['amount'])
            elif n['name'] == 'Carbohydrates': carbs = round(n['amount'])
            elif n['name'] == 'Fat': fat = round(n['amount'])

        # Update meal
        old_meal.meal_name = recipe['title']
        old_meal.calories = recipe.get('calories', target_calories)
        old_meal.protein = protein
        old_meal.carbs = carbs
        old_meal.fats = fat
        old_meal.image_url = recipe.get('image', '')
        old_meal.save()

        return JsonResponse({
            'success': True,
            'meal_name': old_meal.meal_name,
            'calories': old_meal.calories,
            'image_url': old_meal.image_url,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@login_required
def discover_meals(request):
    profile = request.user.profile
    calorie_target = profile.calculate_tdee()
    target_per_meal = calorie_target // 4

    diet = ""
    intolerances = ""
    if profile.health_issues:
        issues = profile.health_issues.lower()
        if "diabetes" in issues: diet = "low glycemic"
        if "gluten" in issues: intolerances = "gluten"

    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        'apiKey': settings.SPOONACULAR_API_KEY,
        'number': 20,
        'minCalories': max(100, target_per_meal - 150),
        'maxCalories': target_per_meal + 150,
        'diet': diet,
        'intolerances': intolerances,
        'addRecipeInformation': True,
        'fillIngredients': True,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        recipes = response.json().get('results', [])
    except Exception as e:
        print("API Error:", e)
        recipes = []

    return render(request, 'meals/discover.html', {'recipes': recipes})
import json
from django.http import JsonResponse

@login_required
def add_meal_to_plan(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        user = request.user

        # Validate required fields
        required = ['name', 'calories', 'day', 'meal_type']
        for field in required:
            if not data.get(field):
                return JsonResponse({'error': f'Missing field: {field}'}, status=400)

        # Create or update meal plan entry
        meal, created = MealPlan.objects.update_or_create(
            user=user,
            day=data['day'],
            meal_type=data['meal_type'],
            defaults={
                'meal_name': data['name'],
                'calories': int(data['calories']),
                'image_url': data.get('image', ''),
                'protein': 0,  # You can enhance this later
                'carbs': 0,
                'fats': 0,
            }
        )

        return JsonResponse({'success': True, 'meal_id': meal.id})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
from django.utils import timezone

@login_required
def toggle_meal_eaten(request, meal_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        meal = MealPlan.objects.get(id=meal_id, user=request.user)
        meal.eaten = not meal.eaten
        if meal.eaten:
            meal.eaten_at = timezone.now()
        else:
            meal.eaten_at = None
        meal.save()

        return JsonResponse({'success': True, 'eaten': meal.eaten})

    except MealPlan.DoesNotExist:
        return JsonResponse({'error': 'Meal not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)