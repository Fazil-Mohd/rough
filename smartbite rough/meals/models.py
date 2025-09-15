from django.db import models
from django.contrib.auth.models import User

# meals/models.py
class MealPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    day = models.CharField(max_length=10)
    meal_type = models.CharField(max_length=20)
    meal_name = models.CharField(max_length=200)
    calories = models.IntegerField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fats = models.FloatField()
    image_url = models.URLField(max_length=500, blank=True, null=True)  # 👈 NEW FIELD
    image_url = models.URLField(max_length=500, blank=True, null=True)
    eaten = models.BooleanField(default=False)          # 👈 NEW
    eaten_at = models.DateTimeField(null=True, blank=True)  # 👈 NEW

    def __str__(self):
        return f"{self.user.username} - {self.day} {self.meal_type}: {self.meal_name}"