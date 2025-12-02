from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


# class Category(models.Model):
#    name = models.CharField(max_length=100, db_index=True)
#    slug = models.CharField(max_length=100, unique=True)

#    class Meta:
#       ordering = ('name', )
#       verbose_name = 'Category'
#       verbose_name_plural = 'Categories'

#    def __str__(self):
#       return self.name
   
#    def get_absolute_url(self):
#       return reverse("myapp:product_list_by_category", args=[self.slug])
   
# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
        ('superadmin', 'SuperAdmin'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    # Add custom related names to avoid clashing with default user-related models
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',  # Custom related name to prevent clashes
        blank=True
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',  # Custom related name to prevent clashes
        blank=True
    )

    def __str__(self):
        return self.username


# Модель Категории
class Category(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=200, blank=True)  # Добавляем поле title
    slug = models.SlugField(max_length=100, unique=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

# Обновляем модель Item - добавляем связь с категориями
class Item(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=100, unique=True)
    image = models.ImageField(upload_to='items/%Y/%m/%d', blank=True, null=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    # Добавляем связь с категориями
    categories = models.ManyToManyField(Category, blank=True, related_name='items')

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name
   
    def get_absolute_url(self):
        return reverse("myapp:item_detail", args=[self.id, self.slug])

# Модель Заказа (для покупок и истории) - ДОЛЖНА БЫТЬ ПОСЛЕ Item
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='orders')
    quantity = models.IntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"Order {self.id} - {self.user.username}"