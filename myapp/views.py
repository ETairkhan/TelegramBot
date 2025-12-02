from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from .serializers import UserSerializer, ItemSerializer
from .models import Item
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .permissions import IsAdmin, IsSuperAdmin, IsUser

from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token




User = get_user_model() 

class UserList(APIView):
    permission_classes = [IsSuperAdmin]  
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

class UserDetail(APIView):
    permission_classes = [IsSuperAdmin]
    def get(self, request, pk):
        user = User.objects.get(pk=pk)
        serializer = UserSerializer(user)
        return Response(serializer.data)

class UserCreate(APIView):
    permission_classes = [IsSuperAdmin] 
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserUpdate(APIView):
    permission_classes = [IsSuperAdmin]  
    def put(self, request, pk):
        user = User.objects.get(pk=pk)
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserDelete(APIView):
    permission_classes = [IsSuperAdmin]  
    def delete(self, request, pk):
        user = User.objects.get(pk=pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ItemList(APIView):
    permission_classes = [IsAuthenticated]  
    def get(self, request):
        items = Item.objects.all()
        serializer =  ItemSerializer(items, many=True)
        return Response(serializer.data)
    
class ItemDetail(APIView):
    permission_classes = [IsAuthenticated]  
    def get(self, request, pk):
        try:
            item = Item.objects.get(pk=pk)
            serializer = ItemSerializer(item)
            return Response(serializer.data)
        except Item.DoesNotExist: 
            return Response({"error" : "Item not found"}, status=status.HTTP_404_NOT_FOUND)

class ItemCreate(APIView):
    permission_classes = [IsAdmin]
    def post(self,request):
        serializer = ItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

class ItemUpdate(APIView):
    permission_classes = [IsAdmin]
    def put(self, request, pk):
        try:
            item = Item.objects.get(pk=pk)
            serializer = ItemSerializer(item, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Item.DoesNotExist:
            return Response({"error" : "Item not found"}, status=status.HTTP_404_NOT_FOUND)

class ItemDelete(APIView):
    permission_classes = [IsAdmin]
    def delete(self, request, pk):
        try:
            item = Item.objects.get(pk=pk)
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Item.DoesNotExist:
            return Response({"error" : "Item not found"}, status=status.HTTP_404_NOT_FOUND)
        
    


@api_view(['POST'])
def api_token_login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    # Authenticate user with Django's authentication system
    user = authenticate(username=username, password=password)
    
    if user is not None:
        # Get or create token for the user
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'success': True,
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        })
    else:
        return Response({
            'success': False,
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
from .models import Category, Order
from .serializers import CategorySerializer, OrderSerializer

# Category APIs
class CategoryList(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

class CategoryCreate(APIView):
    permission_classes = [IsAdmin]
    
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Order APIs
class OrderCreate(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Пользователь может покупать только для себя
        data = request.data.copy()
        data['user'] = request.user.id
        
        serializer = OrderSerializer(data=data)
        if serializer.is_valid():
            # Рассчитываем общую цену
            item_id = data.get('item')
            quantity = data.get('quantity', 1)
            
            try:
                item = Item.objects.get(id=item_id)
                total_price = item.price * quantity
                
                # Создаем заказ
                order = serializer.save(
                    user=request.user,
                    total_price=total_price,
                    status='completed'  # Сразу завершаем покупку
                )
                
                return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
                
            except Item.DoesNotExist:
                return Response({"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrderList(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Пользователь видит только свои заказы
        # Админ/суперадмин могут видеть все заказы
        if request.user.role in ['admin', 'superadmin']:
            orders = Order.objects.all()
        else:
            orders = Order.objects.filter(user=request.user)
        
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

class OrderDetail(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            # Проверяем что пользователь имеет доступ к этому заказу
            if order.user != request.user and request.user.role not in ['admin', 'superadmin']:
                return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = OrderSerializer(order)
            return Response(serializer.data)
            
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)