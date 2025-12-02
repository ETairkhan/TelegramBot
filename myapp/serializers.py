from django.contrib.auth import get_user_model
from .models import Item
from rest_framework import serializers

CustomUser = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)  # Make password write-only and required
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'password']
    
    def create(self, validated_data):
        # Extract password from validated data
        password = validated_data.pop('password')
        
        # Set superuser status based on role
        if validated_data.get('role') == 'superadmin':
            validated_data['is_superuser'] = True
            validated_data['is_staff'] = True
        else:
            validated_data['is_superuser'] = False
            validated_data['is_staff'] = False
        
        # Create user
        user = CustomUser.objects.create(**validated_data)
        # Set password properly (this hashes it)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        # Handle password if provided
        password = validated_data.pop('password', None)
        
        # Update role and superuser status if role is being changed
        if 'role' in validated_data:
            if validated_data['role'] == 'superadmin':
                validated_data['is_superuser'] = True
                validated_data['is_staff'] = True
            else:
                validated_data['is_superuser'] = False
                validated_data['is_staff'] = False
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update password if provided
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance

from .models import Category, Order

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'title', 'slug']

class OrderSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_price = serializers.DecimalField(source='item.price', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'user', 'item', 'item_name', 'item_price', 'quantity', 'total_price', 'status', 'created_at']
        read_only_fields = ['user', 'total_price']

# Обновляем ItemSerializer чтобы включить категории
class ItemSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Item
        fields = ['id', 'name', 'slug', 'image', 'description', 'price', 'available', 'created', 'updated', 'categories', 'category_ids']
    
    def create(self, validated_data):
        category_ids = validated_data.pop('category_ids', [])
        item = Item.objects.create(**validated_data)
        
        # Добавляем категории если переданы
        if category_ids:
            categories = Category.objects.filter(id__in=category_ids)
            item.categories.set(categories)
        
        return item
    
    def update(self, instance, validated_data):
        category_ids = validated_data.pop('category_ids', None)
        
        # Обновляем основные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Обновляем категории если переданы
        if category_ids is not None:
            categories = Category.objects.filter(id__in=category_ids)
            instance.categories.set(categories)
        
        return instance