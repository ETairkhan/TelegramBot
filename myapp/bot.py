import logging
from dotenv import load_dotenv
import os
import sys
import django
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import Router
from aiogram import F
import aiohttp
import asyncio
from asgiref.sync import sync_to_async
import base64

load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.append(project_dir)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from myapp.models import Item
API_TOKEN = os.getenv("API_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")

if not API_TOKEN:
    raise ValueError("❌ API_TOKEN is missing in .env")
if not API_BASE_URL:
    raise ValueError("❌ API_BASE_URL is missing in .env")


# Use your actual superadmin credentials
DEFAULT_USERNAME = os.getenv("DEFAULT_USERNAME")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD")

user_login_state = {}

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

dp.include_router(router)

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
    
    async def login(self, username, password):
        """Login and get token"""
        login_data = {
            'username': username,
            'password': password
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/token-login/", json=login_data) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data.get('token')
                    return data, response.status
                else:
                    return await response.json(), response.status
    
    async def make_request(self, method, endpoint, data=None):
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if self.token:
            headers['Authorization'] = f'Token {self.token}'
        
        
            # Debug logging
        print(f"🔧 API Request: {method} {url}")
        print(f"🔧 Headers: {headers}")
        print(f"🔧 Data: {data}")
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=data, headers=headers) as response:
                print(f"🔧 API Response Status: {response.status}")
                
                if response.status == 200 or response.status == 201:
                    result = await response.json()
                    print(f"🔧 API Response Data: {result}")
                    return result, response.status
                else:
                    try:
                        error_text = await response.json()
                        print(f"🔧 API Error JSON: {error_text}")
                    except:
                        error_text = await response.text()
                        print(f"🔧 API Error Text: {error_text}")
                    return error_text, response.status

    async def get_users(self):
        return await self.make_request('GET', '/users/')
    
    async def get_user(self, user_id):
        return await self.make_request('GET', f'/user/{user_id}/')
    
    async def create_user(self, user_data):
        return await self.make_request('POST', '/user/create/', user_data)
    
    async def update_user(self, user_id, user_data):
        return await self.make_request('PUT', f'/user/{user_id}/edit/', user_data)
    
    async def delete_user(self, user_id):
        return await self.make_request('DELETE', f'/user/{user_id}/delete/')
    
    async def get_items(self):
        return await self.make_request('GET', '/items/')
    
    async def get_item(self, item_id):
        return await self.make_request('GET', f'/items/{item_id}/')
    
    async def create_item(self, item_data):
        return await self.make_request('POST', '/items/create/', item_data)
    
    async def update_item(self, item_id, item_data):
        return await self.make_request('PUT', f'/items/{item_id}/edit/', item_data)
    
    async def delete_item(self, item_id):
        return await self.make_request('DELETE', f'/items/{item_id}/delete/')

    async def get_categories(self):
        return await self.make_request('GET', '/categories/')

    async def create_category(self, category_data):
        return await self.make_request('POST', '/categories/create/', category_data)

    async def get_orders(self):
        return await self.make_request('GET', '/orders/')

    async def create_order(self, order_data):
        return await self.make_request('POST', '/orders/create/', order_data)

    async def get_order(self, order_id):
        return await self.make_request('GET', f'/orders/{order_id}/')

api_client = APIClient(API_BASE_URL)

@router.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Привет! Для входа в систему, введи логин и пароль через пробел\nПример: `username password`", parse_mode='Markdown')
    user_login_state[message.from_user.id] = {"is_logged_in": False, "waiting_for_login": True}

logging.basicConfig(level=logging.INFO)

async def show_available_commands(message: types.Message, role='user'):
    """Send available commands based on user role after successful login."""
    
    common_commands = """
ℹ️ **Общие команды:**
/help - Показать это сообщение
/logout - Выйти из системы
"""
    
    user_commands = """
👤 **Команды для пользователей:**
/item_info <id> - Показать информацию о товаре
/list_items - Показать список всех товаров
/list_categories - Список категорий
/buy_item <id> [количество] - Купить товар
/my_orders - Мои заказы (история покупок)
"""

    admin_commands = """
🛍️ **Команды администратора:**
/item_info <id> - Показать информацию о товаре
/list_items - Показать список всех товаров
/create_item - Создать новый товар
/update_item <id> - Обновить товар
/delete_item <id> - Удалить товар
/create_category - Создать категорию
/list_categories - Список категорий
/list_orders - Все заказы (админ видит все)
"""

    superadmin_commands = """
👥 **Команды суперадминистратора:**
/create_user - Создать нового пользователя
/list_users - Показать список всех пользователей
/user_info <id> - Показать информацию о конкретном пользователе
/update_user <id> - Обновить данные пользователя
/delete_user <id> - Удалить пользователя (по ID)
"""

    # Build help text based on role
    help_text = f"📋 **Доступные команды для роли: {role}**\n"
    
    if role == 'user':
        help_text += user_commands + common_commands
    elif role == 'admin':
        help_text +=  admin_commands + common_commands
    elif role == 'superadmin':
        help_text +=  superadmin_commands + common_commands
    
    help_text += """
📝 **Примеры:**
/user_info 1
/item_info 1
/list_items
"""
    
    await message.reply(help_text)

@router.message(F.text & ~F.text.startswith('/'))
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})

    # Handle item creation/update first
    if state.get("creating_item"):
        await handle_item_creation(message)
        return
    
    # Handle category creation FIRST
    if state.get("creating_category"):
        await handle_category_creation(message)
        return
    

    # Handle user creation
    if state.get("creating_user"):
        await handle_user_creation(message)
        return
    
    # Handle user update (if using interactive method)
    if state.get("updating_user"):
        await handle_user_update(message)
        return


    if state.get("updating_item"):
        await handle_item_update(message)
        return

    # Handle login - only if waiting for login after /start
    if state.get("waiting_for_login") and not state.get("is_logged_in", False):
        parts = message.text.split()
        
        if len(parts) == 2:
            username, password = parts[0], parts[1]
            
            try:
                # Use token-based login
                response, status_code = await api_client.login(username, password)
                
                if status_code == 200 and response.get('success'):
                    # ✅ CRITICAL: Store the token in api_client for future requests
                    api_client.token = response.get('token')
                    
                    # Successful login
                    user_data = response['user']
                    user_login_state[user_id] = {
                        "is_logged_in": True,
                        "username": username,
                        "user_id": user_data['id'],
                        "role": user_data['role'],
                        "waiting_for_login": False
                    }
                    
                    await message.reply(f"✅ Добро пожаловать, {username}! Вы успешно вошли в систему как {user_data['role']}.")
                    await show_available_commands(message, user_data['role'])
                    return
                else:
                    error_msg = response.get('error', 'Invalid credentials')
                    await message.reply(f"❌ Ошибка входа: {error_msg}\nПопробуйте снова или используйте /start для повторной попытки.")
                    return
                    
            except Exception as e:
                logging.error(f"Login error: {e}")
                await message.reply("❌ Ошибка при подключении к серверу. Проверьте, запущен ли сервер Django.")
                return
        else:
            await message.reply("🔐 Пожалуйста, введите логин и пароль через пробел.\nПример: `username password`\nИли используйте /start для повторной попытки.", parse_mode='Markdown')
            return
        
    # If already logged in but sent random text
    if state.get("is_logged_in", False):
        await message.reply("ℹ️ Используйте /help для просмотра доступных команд.")
        return
    
    # If not logged in and not waiting for login
    await message.reply("🔐 Используйте /start для входа в систему.")

@router.message(Command("create_user"))
async def create_user_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    # Check if user has permission (superadmin only)
    if state.get('role') != 'superadmin':
        await message.reply("❌ У вас нет прав для создания пользователей. Требуется роль superadmin.")
        return
    
    instructions = """
👤 **Создание нового пользователя**

Отправьте данные пользователя в формате:
username: имя_пользователя
email: email@example.com
password: пароль
role: user/admin/superadmin

**Пример:**
username: TairkhanWhyJava
email: tair@example.com
password: securepassword123
role: user

*Поля `username`, `email` и `password` обязательны!*
*Роль по умолчанию: `user`*
"""
    await message.reply(instructions)
    
    # Set state for user creation
    user_login_state[user_id]["creating_user"] = True

async def handle_user_creation(message: types.Message):
    user_id = message.from_user.id
    try:
        data_lines = message.text.strip().split('\n')
        user_data = {}
        
        required_fields = ['username', 'email', 'password']
        missing_fields = []
        
        for line in data_lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'username':
                    user_data['username'] = value
                elif key == 'email':
                    user_data['email'] = value
                elif key == 'password':
                    user_data['password'] = value
                elif key == 'role':
                    if value.lower() in ['user', 'admin', 'superadmin']:
                        user_data['role'] = value.lower()
                    else:
                        await message.reply("❌ Ошибка: роль должна быть 'user', 'admin' или 'superadmin'")
                        user_login_state[user_id]["creating_user"] = False
                        return
        
        # Check for required fields
        for field in required_fields:
            if field not in user_data:
                missing_fields.append(field)
        
        if missing_fields:
            await message.reply(f"❌ Отсутствуют обязательные поля: {', '.join(missing_fields)}")
            user_login_state[user_id]["creating_user"] = False
            return
        
        # Set default role if not provided
        if 'role' not in user_data:
            user_data['role'] = 'user'
        
        # Use API to create user
        response, status_code = await api_client.create_user(user_data)
        
        if status_code == 201:
            await message.reply(f"✅ Пользователь '{user_data['username']}' успешно создан!")
            
            user_info = f"""
👤 **Создан новый пользователь:**

🆔 Username: {user_data['username']}
📧 Email: {user_data['email']}
🎭 Role: {user_data['role']}
"""
            await message.reply(user_info)
        elif status_code == 400:
            if isinstance(response, dict):
                if 'username' in response:
                    await message.reply(f"❌ Пользователь с именем '{user_data['username']}' уже существует!")
                elif 'email' in response:
                    await message.reply(f"❌ Пользователь с email '{user_data['email']}' уже существует!")
                else:
                    await message.reply(f"❌ Ошибка при создании пользователя: {response}")
            else:
                await message.reply(f"❌ Ошибка при создании пользователя: {response}")
        else:
            await message.reply(f"❌ Ошибка API: статус {status_code}, ответ: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла непредвиденная ошибка: {str(e)}")
    
    # Clear creation state
    user_login_state[user_id]["creating_user"] = False

@router.message(Command("list_users"))
async def list_users(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return

    if state.get('role') != 'superadmin':
        await message.reply("❌ У вас нет прав для просмотра списка пользователей. Требуется роль superadmin.")
        return
    
    try:
        response, status_code = await api_client.get_users()
        
        if status_code == 200 and response:
            users_list = "\n".join([f"👤 {user['id']}: {user['username']} ({user['email']}) - {user.get('role', 'user')}" 
                                  for user in response])
            await message.reply(f"📋 Список пользователей:\n{users_list}")
        elif status_code == 200 and not response:
            await message.reply("ℹ️ Нет зарегистрированных пользователей.")
        else:
            await message.reply(f"❌ Ошибка при получении списка пользователей: статус {status_code}, ответ: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {e}")

@router.message(Command("user_info"))
async def user_info(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Использование: /user_info <id_пользователя>")
            return
        
        user_id_param = parts[1]
        response, status_code = await api_client.get_user(user_id_param)
        
        if status_code == 200:
            user = response
            user_info_lines = [
                "👤 Информация о пользователе:",
                f"🆔 ID: {user.get('id', 'N/A')}",
                f"👤 Username: {user.get('username', 'N/A')}",
                f"📧 Email: {user.get('email', 'N/A')}",
                f"🎭 Role: {user.get('role', 'user')}",
                f"✅ Active: {'Yes' if user.get('is_active', True) else 'No'}"
            ]
            
            await message.reply("\n".join(user_info_lines))
            
        elif status_code == 404:
            await message.reply(f"❌ Пользователь с ID {user_id_param} не найден.")
        else:
            await message.reply(f"❌ Ошибка: статус {status_code}, ответ: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {str(e)}")

@router.message(Command("update_user"))
async def update_user_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Использование: /update_user <id_пользователя>")
            return
        
        user_id_param = parts[1]
        
        # Verify user exists first
        response, status_code = await api_client.get_user(user_id_param)
        if status_code != 200:
            await message.reply(f"❌ Пользователь с ID {user_id_param} не найден.")
            return

        instructions = f"""
👤 **Обновление пользователя ID {user_id_param}**

Отправьте данные для обновления в формате:
username: Новое имя пользователя
email: Новый email
password: Новый пароль

**Отправьте только те поля, которые хотите обновить.**

📝 **Пример:**
username: AYALUBLU
email: ayalublu@gmail.com
password: newsecurepassword123
"""
        await message.reply(instructions)
        
        user_login_state[user_id]["updating_user"] = True
        user_login_state[user_id]["updating_user_id"] = user_id_param
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {e}")

async def handle_user_update(message: types.Message):
    user_id = message.from_user.id
    try:
        user_id_param = user_login_state[user_id].get("updating_user_id")
        
        if not user_id_param:
            await message.reply("❌ Ошибка: ID пользователя не найден")
            user_login_state[user_id]["updating_user"] = False
            return
        
        data_lines = message.text.strip().split('\n')
        user_data = {}
        
        for line in data_lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'username':
                    user_data['username'] = value
                elif key == 'email':
                    user_data['email'] = value
                elif key == 'password':
                    user_data['password'] = value
        
        if not user_data:
            await message.reply("❌ Не указаны данные для обновления")
            user_login_state[user_id]["updating_user"] = False
            return
        
        response, status_code = await api_client.update_user(user_id_param, user_data)
        
        if status_code == 200:
            updated_fields = []
            if 'username' in user_data:
                updated_fields.append(f"👤 Username: {user_data['username']}")
            if 'email' in user_data:
                updated_fields.append(f"📧 Email: {user_data['email']}")
            if 'password' in user_data:
                updated_fields.append("🔑 Password: обновлен")
            
            response_text = f"✅ Пользователь с ID {user_id_param} успешно обновлен!\n"
            if updated_fields:
                response_text += "\n".join(updated_fields)
            
            await message.reply(response_text)
            
        elif status_code == 404:
            await message.reply(f"❌ Пользователь с ID {user_id_param} не найден")
        else:
            error_msg = f"Ошибка: {response}" if response else "Неизвестная ошибка"
            await message.reply(f"❌ Ошибка при обновлении пользователя: {error_msg}")
        
    except Exception as e:
        await message.reply(f"❌ Произошла непредвиденная ошибка: {str(e)}")
    
    user_login_state[user_id]["updating_user"] = False
    user_login_state[user_id]["updating_user_id"] = None

@router.message(Command("delete_user"))
async def delete_user(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Использование: /delete_user <id_пользователя>")
            return
        
        user_id_param = parts[1]
        response, status_code = await api_client.delete_user(user_id_param)
        
        if status_code == 204:
            await message.reply(f"✅ Пользователь с ID {user_id_param} успешно удален.")
        elif status_code == 404:
            await message.reply(f"❌ Пользователь с ID {user_id_param} не найден.")
        else:
            await message.reply(f"❌ Ошибка при удалении пользователя: статус {status_code}, ответ: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {e}")

@router.message(Command("list_items"))
async def list_items_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    try:
        response, status_code = await api_client.get_items()
        
        if status_code == 200 and response:
            items_list = []
            for item in response:
                # Формируем информацию о категориях
                categories_info = ""
                if item.get('categories'):
                    category_names = [cat['name'] for cat in item['categories']]
                    categories_info = f" | 📁 {', '.join(category_names)}"
                
                items_list.append(f"🛍️ {item['id']}: {item['name']} - 💰 {item['price']} ₸{categories_info}")
            
            items_text = "\n".join(items_list)
            await message.reply(f"📋 Список товаров:\n{items_text}")
        elif status_code == 200 and not response:
            await message.reply("ℹ️ Нет товаров в базе данных.")
        else:
            await message.reply(f"❌ Ошибка при получении списка товаров: статус {status_code}, ответ: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {e}")


@router.message(Command("item_info"))
async def item_info_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Использование: /item_info <id_товара>")
            return
        
        item_id = parts[1]
        response, status_code = await api_client.get_item(item_id)
        
        if status_code == 200:
            item = response
            item_info_lines = [
                "🛍️ Информация о товаре:",
                f"🆔 ID: {item.get('id', 'N/A')}",
                f"📝 Название: {item.get('name', 'N/A')}",
                f"🔗 Slug: {item.get('slug', 'N/A')}",
                f"📋 Описание: {item.get('description', 'Не указано')}",
                f"💰 Цена: {item.get('price', 0)} ₸",
                f"✅ Доступен: {'Да' if item.get('available', True) else 'Нет'}"
            ]
            
            # Добавляем информацию о категориях
            if item.get('categories'):
                category_names = [f"{cat['name']} (ID: {cat['id']})" for cat in item['categories']]
                item_info_lines.append(f"📁 Категории: {', '.join(category_names)}")
            else:
                item_info_lines.append("📁 Категории: Не указаны")
            
            await message.reply("\n".join(item_info_lines))
            
        elif status_code == 404:
            await message.reply(f"❌ Товар с ID {item_id} не найден.")
        else:
            await message.reply(f"❌ Ошибка: статус {status_code}, ответ: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {str(e)}")

@router.message(Command("create_item"))
async def create_item_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    try:
        instructions = """
📝 **Создание нового товара**

Отправьте данные в формате:
name: Название товара
slug: уникальный-слаг
description: Описание товара
price: 99.99
available: true
category_ids: 1,2,3

**Пример:**
name: iPhone 15
slug: iphone-15
description: Новый iPhone 15 с улучшенной камерой
price: 799.99
available: true
category_ids: 1,2,3

*Поля `name` и `slug` обязательны!*
*`category_ids` - ID категорий через запятую (необязательно)*

📋 **Сначала посмотрите список категорий:**
**Категории должны быть из списка существующих!**
/list_categories
"""
        await message.reply(instructions)
        
        user_login_state[user_id]["creating_item"] = True
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {e}")

async def handle_item_creation(message: types.Message):
    user_id = message.from_user.id
    try:
        data_lines = message.text.strip().split('\n')
        item_data = {}
        
        for line in data_lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'name':
                    item_data['name'] = value
                elif key == 'slug':
                    slug = value.lower().replace(' ', '-')
                    if not all(c.isalnum() or c == '-' for c in slug):
                        await message.reply("❌ Ошибка: slug может содержать только латинские буквы, цифры и дефисы!")
                        return
                    item_data['slug'] = slug
                elif key == 'description':
                    item_data['description'] = value
                elif key == 'price':
                    try:
                        item_data['price'] = float(value)
                    except ValueError:
                        await message.reply("❌ Ошибка: цена должна быть числом (например: 99.99)")
                        return
                elif key == 'available':
                    item_data['available'] = value.lower() in ['true', 'yes', 'да', '1', 'on']
                elif key == 'category_ids':
                    try:
                        # Проверяем существование категорий
                        categories_response, status = await api_client.get_categories()
                        if status != 200:
                            await message.reply("❌ Ошибка: не удалось получить список категорий")
                            return
                        
                        existing_categories = [str(cat['id']) for cat in categories_response]
                        category_ids = [cat_id.strip() for cat_id in value.split(',')]
                        
                        # Проверяем каждую категорию
                        invalid_categories = []
                        for cat_id in category_ids:
                            if cat_id not in existing_categories:
                                invalid_categories.append(cat_id)
                        
                        if invalid_categories:
                            await message.reply(f"❌ Ошибка: следующие категории не существуют: {', '.join(invalid_categories)}")
                            return
                        
                        item_data['category_ids'] = [int(cat_id) for cat_id in category_ids]
                    except Exception as e:
                        await message.reply(f"❌ Ошибка в формате category_ids: {e}")
                        return
        
        # Проверяем обязательные поля
        required_fields = ['name', 'slug', 'price']
        for field in required_fields:
            if field not in item_data:
                await message.reply(f"❌ Обязательное поле '{field}' отсутствует")
                return
        
        response, status_code = await api_client.create_item(item_data)
        
        if status_code == 201:
            await message.reply("✅ Товар успешно создан! 🎉")
            
            # Показываем созданный товар
            item_info = [
                f"📦 **Созданный товар:**",
                f"• Название: {item_data['name']}",
                f"• Slug: {item_data['slug']}",
                f"• Описание: {item_data.get('description', 'Не указано')}",
                f"• Цена: {item_data['price']} ₸",
                f"• Доступен: {'Да' if item_data.get('available', True) else 'Нет'}",
                f"• Категории: {item_data.get('category_ids', [])}"
            ]
            await message.reply("\n".join(item_info))
            
        else:
            error_msg = f"Ошибка: {response}" if response else "Неизвестная ошибка"
            await message.reply(f"❌ Ошибка при создании товара: {error_msg}")
        
    except Exception as e:
        await message.reply(f"❌ Произошла непредвиденная ошибка: {str(e)}")
    
    user_login_state[user_id]["creating_item"] = False


@router.message(lambda message: message.photo and user_login_state.get(message.from_user.id, {}).get("waiting_for_image", False))
async def handle_image(message: types.Message):
    user_id = message.from_user.id
    try:
        file_id = message.photo[-1].file_id
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path

        file = await bot.download_file(file_path)

        import uuid
        file_name = f"{uuid.uuid4().hex}.jpg"
        file_path_on_server = os.path.join("items", file_name)
    
        os.makedirs(os.path.dirname(file_path_on_server), exist_ok=True)

        with open(file_path_on_server, 'wb') as f:
            f.write(file.getvalue())

        user_login_state[user_id]["waiting_for_image"] = False
        user_login_state[user_id]["waiting_for_text"] = True 
        user_login_state[user_id]["image_path"] = file_path_on_server
        print(user_login_state)

        await message.reply(f"Изображение получено и сохранено как {file_name}. Теперь отправьте данные товара.")

    except Exception as e:
        await message.reply(f"❌ Произошла ошибка при обработке изображения: {e}")


@router.message(Command("update_item"))
async def update_item_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Использование: /update_item <id_товара>")
            return
        
        item_id = parts[1]
        
        # Verify item exists
        response, status_code = await api_client.get_item(item_id)
        if status_code != 200:
            await message.reply(f"❌ Товар с ID {item_id} не найден.")
            return

        # Получаем список категорий для справки
        categories_response, status = await api_client.get_categories()
        if status == 200:
            categories_info = "\n".join([f"  - {cat['id']}: {cat['name']}" for cat in categories_response])
            categories_text = f"\n📋 **Существующие категории:**\n{categories_info}"
        else:
            categories_text = ""

        instructions = f"""
📝 **Обновление товара ID {item_id}**

Отправьте данные для обновления в формате:
name: Name
slug: slug
description: Description
price: 149.99
available: false
category_ids: 1,2,3
{categories_text}

**Отправьте только те поля, которые хотите обновить.**
**Для category_ids используйте только существующие ID категорий!**
"""
        await message.reply(instructions)
        
        user_login_state[user_id]["updating_item"] = True
        user_login_state[user_id]["updating_item_id"] = item_id
        
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {e}")



async def handle_item_update(message: types.Message):
    user_id = message.from_user.id
    try:
        item_id = user_login_state[user_id].get("updating_item_id")
        
        if not item_id:
            await message.reply("❌ Ошибка: ID товара не найден")
            user_login_state[user_id]["updating_item"] = False
            return
        
        data_lines = message.text.strip().split('\n')
        item_data = {}
        
        for line in data_lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'name':
                    item_data['name'] = value
                elif key == 'slug':
                    slug = value.lower().replace(' ', '-')
                    if not all(c.isalnum() or c == '-' for c in slug):
                        await message.reply("❌ Ошибка: slug может содержать только латинские буквы, цифры и дефисы!")
                        return
                    item_data['slug'] = slug
                elif key == 'description':
                    item_data['description'] = value
                elif key == 'price':
                    try:
                        item_data['price'] = float(value)
                    except ValueError:
                        await message.reply("❌ Ошибка: цена должна быть числом (например: 99.99)")
                        return
                elif key == 'available':
                    item_data['available'] = value.lower() in ['true', 'yes', 'да', '1', 'on']
                # В функции handle_item_update, внутри цикла обработки полей, добавьте:
                elif key == 'category_ids':
                    try:
                        # Проверяем существование категорий
                        categories_response, status = await api_client.get_categories()
                        if status != 200:
                            await message.reply("❌ Ошибка: не удалось получить список категорий")
                            return
                        
                        existing_categories = [str(cat['id']) for cat in categories_response]
                        category_ids = [cat_id.strip() for cat_id in value.split(',')]
                        
                        # Проверяем каждую категорию
                        invalid_categories = []
                        for cat_id in category_ids:
                            if cat_id not in existing_categories:
                                invalid_categories.append(cat_id)
                        
                        if invalid_categories:
                            await message.reply(f"❌ Ошибка: следующие категории не существуют: {', '.join(invalid_categories)}")
                            return
                        
                        item_data['category_ids'] = [int(cat_id) for cat_id in category_ids]
                    except Exception as e:
                        await message.reply(f"❌ Ошибка в формате category_ids: {e}")
                        return
                        
        if not item_data:
            await message.reply("❌ Не указаны данные для обновления")
            user_login_state[user_id]["updating_item"] = False
            return
        
        response, status_code = await api_client.update_item(item_id, item_data)
        
        if status_code == 200:
            await message.reply(f"✅ Товар с ID {item_id} успешно обновлен! 🎉")
            
            updated_info = ["🔄 Обновленные поля:"]
            for key, value in item_data.items():
                if key == 'available':
                    value = 'Да' if value else 'Нет'
                elif key == 'price':
                    value = f"{value} ₸"
                updated_info.append(f"• {key}: {value}")
            
            await message.reply("\n".join(updated_info))
            
        elif status_code == 404:
            await message.reply(f"❌ Товар с ID {item_id} не найден")
        else:
            error_msg = f"Ошибка: {response}" if response else "Неизвестная ошибка"
            await message.reply(f"❌ Ошибка при обновлении товара: {error_msg}")
        
    except Exception as e:
        await message.reply(f"❌ Произошла непредвиденная ошибка: {str(e)}")
    
    user_login_state[user_id]["updating_item"] = False
    user_login_state[user_id]["updating_item_id"] = None

@router.message(Command("delete_item"))
async def delete_item_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Использование: /delete_item <id_товара>")
            return
        
        item_id = parts[1]
        response, status_code = await api_client.delete_item(item_id)
        
        if status_code == 204:
            await message.reply(f"✅ Товар с ID {item_id} успешно удален.")
        elif status_code == 404:
            await message.reply(f"❌ Товар с ID {item_id} не найден.")
        else:
            await message.reply(f"❌ Ошибка при удалении товара: статус {status_code}, ответ: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {e}")

# ========== ORDER COMMANDS ==========
@router.message(Command("buy_item"))
async def buy_item_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Использование: /buy_item <id_товара> [количество]\nПример: /buy_item 1 2")
            return
        
        item_id = parts[1]
        quantity = int(parts[2]) if len(parts) > 2 else 1
        
        # Create order data
        order_data = {
            "item": item_id,
            "quantity": quantity
        }
        
        response, status_code = await api_client.create_order(order_data)
        
        if status_code == 201:
            await message.reply(f"✅ Покупка успешно оформлена! 🎉")
            
            order_info = f"""
🧾 **Детали заказа:**

🆔 ID заказа: {response.get('id')}
📦 Товар: {response.get('item_name')}
💰 Цена за шт: {response.get('item_price')} ₸
📊 Количество: {response.get('quantity')}
💵 Итого: {response.get('total_price')} ₸
📅 Дата: {response.get('created_at', '')[:16]}
"""
            await message.reply(order_info)
        elif status_code == 404:
            await message.reply("❌ Товар не найден.")
        else:
            await message.reply(f"❌ Ошибка при покупке: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {str(e)}")

@router.message(Command("my_orders"))
async def my_orders_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    try:
        response, status_code = await api_client.get_orders()
        
        if status_code == 200 and response:
            orders_text = "📋 **История ваших заказов:**\n\n"
            
            for order in response:
                orders_text += f"""
🧾 **Заказ #{order['id']}**
📦 Товар: {order.get('item_name', 'N/A')}
💰 Цена: {order.get('total_price')} ₸
📊 Количество: {order.get('quantity')}
📅 Дата: {order.get('created_at', '')[:16]}
📊 Статус: {order.get('status', 'N/A')}
────────────────────
"""
            await message.reply(orders_text)
        elif status_code == 200 and not response:
            await message.reply("ℹ️ У вас пока нет заказов.")
        else:
            await message.reply(f"❌ Ошибка при получении заказов: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {str(e)}")

@router.message(Command("list_orders"))
async def list_orders_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    # Check if user has permission (admin/superadmin only)
    if state.get('role') not in ['admin', 'superadmin']:
        await message.reply("❌ У вас нет прав для просмотра всех заказов. Требуется роль admin.")
        return
    
    try:
        response, status_code = await api_client.get_orders()
        
        if status_code == 200 and response:
            orders_text = "📋 **Все заказы в системе:**\n\n"
            
            for order in response:
                orders_text += f"""
🧾 **Заказ #{order['id']}**
👤 Пользователь ID: {order.get('user', 'N/A')}
📦 Товар: {order.get('item_name', 'N/A')}
💰 Сумма: {order.get('total_price')} ₸
📊 Количество: {order.get('quantity')}
📅 Дата: {order.get('created_at', '')[:16]}
📊 Статус: {order.get('status', 'N/A')}
────────────────────
"""
            await message.reply(orders_text)
        elif status_code == 200 and not response:
            await message.reply("ℹ️ В системе пока нет заказов.")
        else:
            await message.reply(f"❌ Ошибка при получении заказов: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {str(e)}")

# ========== CATEGORY COMMANDS ==========
@router.message(Command("create_category"))
async def create_category_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    # Check if user has permission (admin only)
    if state.get('role') not in ['admin', 'superadmin']:
        await message.reply("❌ У вас нет прав для создания категорий. Требуется роль admin.")
        return
    
    instructions = """
📁 **Создание новой категории**

Отправьте данные категории в формате:
name: Название категории
title: Описание категории
slug: уникальный-слаг

**Пример:**
name: Носки
title: Различные виды носков
slug: socks

*Поля `name` и `slug` обязательны!*
"""
    await message.reply(instructions)
    
    # Set state for category creation
    user_login_state[user_id]["creating_category"] = True

async def handle_category_creation(message: types.Message):
    user_id = message.from_user.id
    try:
        data_lines = message.text.strip().split('\n')
        category_data = {}
        
        required_fields = ['name', 'slug']
        missing_fields = []
        
        for line in data_lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'name':
                    category_data['name'] = value
                elif key == 'title':
                    category_data['title'] = value
                elif key == 'slug':
                    slug = value.lower().replace(' ', '-')
                    if not all(c.isalnum() or c == '-' for c in slug):
                        await message.reply("❌ Ошибка: slug может содержать только латинские буквы, цифры и дефисы!")
                        user_login_state[user_id]["creating_category"] = False
                        return
                    category_data['slug'] = slug
        
        for field in required_fields:
            if field not in category_data:
                missing_fields.append(field)
        
        if missing_fields:
            await message.reply(f"❌ Отсутствуют обязательные поля: {', '.join(missing_fields)}")
            user_login_state[user_id]["creating_category"] = False
            return
        
        # Use API to create category
        response, status_code = await api_client.create_category(category_data)
        
        if status_code == 201:
            await message.reply(f"✅ Категория '{category_data['name']}' успешно создана!")
            
            category_info = f"""
📁 **Создана новая категория:**

📝 Название: {category_data['name']}
📋 Описание: {category_data.get('title', 'Не указано')}
🔗 Slug: {category_data['slug']}
"""
            await message.reply(category_info)
        else:
            await message.reply(f"❌ Ошибка при создании категории: статус {status_code}, ответ: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла непредвиденная ошибка: {str(e)}")
    
    user_login_state[user_id]["creating_category"] = False

@router.message(Command("list_categories"))
async def list_categories_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Сначала войдите в систему с помощью /start")
        return
    
    try:
        response, status_code = await api_client.get_categories()
        
        if status_code == 200 and response:
            categories_list = "\n".join([f"📁 {cat['id']}: {cat['name']} - {cat.get('title', '')}" 
                                       for cat in response])
            await message.reply(f"📋 Список категорий:\n{categories_list}")
        elif status_code == 200 and not response:
            await message.reply("ℹ️ Нет категорий в базе данных.")
        else:
            await message.reply(f"❌ Ошибка при получении списка категорий: статус {status_code}, ответ: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка: {e}")

@router.message(Command("help"))
async def send_help_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if state.get("is_logged_in"):
        # ✅ Get the user's role from the state and pass it to show_available_commands
        role = state.get('role', 'user')
        await show_available_commands(message, role)
    else:
        await message.reply("ℹ️ Сначала войдите в систему с помощью /start")

@router.message(Command("logout"))
async def logout_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_login_state:
        username = user_login_state[user_id].get('username', '')
        user_login_state[user_id] = {"is_logged_in": False, "waiting_for_login": False}
        api_client.token = None  # ✅ Clear the token
        await message.reply(f"✅ {username}, вы вышли из системы. Используйте /start для входа.")
    else:
        await message.reply("ℹ️ Вы не авторизованы.")


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    print("🤖 Bot is starting...")
    print("✅ Bot is ready!")
    print("🔗 Make sure Django server is running on http://localhost:8000")
    print("🚀 Use /start in Telegram to begin")
    print(f"🔐 Default credentials: {DEFAULT_USERNAME} / {DEFAULT_PASSWORD}")
    asyncio.run(main())