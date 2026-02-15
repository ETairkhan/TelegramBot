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
    raise ValueError("❌ API_TOKEN .env файлында жоқ")
if not API_BASE_URL:
    raise ValueError("❌ API_BASE_URL .env файлында жоқ")

# Нақты superadmin деректерін пайдаланыңыз
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
        """Жүйеге кіру және token алу"""
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
        
            # Debug логирование
        print(f"🔧 API сұранысы: {method} {url}")
        print(f"🔧 Header'лар: {headers}")
        print(f"🔧 Деректер: {data}")
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=data, headers=headers) as response:
                print(f"🔧 API жауап статусы: {response.status}")
                
                if response.status == 200 or response.status == 201:
                    result = await response.json()
                    print(f"🔧 API жауап деректері: {result}")
                    return result, response.status
                else:
                    try:
                        error_text = await response.json()
                        print(f"🔧 API қате JSON: {error_text}")
                    except:
                        error_text = await response.text()
                        print(f"🔧 API қате мәтіні: {error_text}")
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
    await message.reply("Сәлем! Жүйеге кіру үшін, логин мен парольді бос орын арқылы енгізіңіз\nМысалы: `username password`", parse_mode='Markdown')
    user_login_state[message.from_user.id] = {"is_logged_in": False, "waiting_for_login": True}

logging.basicConfig(level=logging.INFO)

async def show_available_commands(message: types.Message, role='user'):
    """Сәтті кіргеннен кейін рөлге байланысты қолжетімді командаларды жіберу"""
    
    common_commands = """
ℹ️ **Ортақ командалар:**
/help - Осы хабарламаны көрсету
/logout - Жүйеден шығу
"""
    
    user_commands = """
👤 **Пайдаланушыларға арналған командалар:**
/item_info <id> - Тауар туралы ақпаратты көрсету
/list_items - Барлық тауарлар тізімін көрсету
/list_categories - Категориялар тізімі
/buy_item <id> [саны] - Тауар сатып алу
/my_orders - Менің тапсырыстарым (сатып алу тарихы)
"""

    admin_commands = """
🛍️ **Администраторға арналған командалар:**
/item_info <id> - Тауар туралы ақпаратты көрсету
/list_items - Барлық тауарлар тізімін көрсету
/create_item - Жаңа тауар құру
/update_item <id> - Тауарды жаңарту
/delete_item <id> - Тауарды жою
/create_category - Категория құру
/list_categories - Категориялар тізімі
/list_orders - Барлық тапсырыстар (админ бәрін көреді)
"""

    superadmin_commands = """
👥 **Суперадминистраторға арналған командалар:**
/create_user - Жаңа пайдаланушы құру
/list_users - Барлық пайдаланушылар тізімін көрсету
/user_info <id> - Нақты пайдаланушы туралы ақпаратты көрсету
/update_user <id> - Пайдаланушы деректерін жаңарту
/delete_user <id> - Пайдаланушыны жою (ID бойынша)
"""

    # Рөлге байланысты анықтама мәтінін құру
    help_text = f"📋 **{role} рөлі үшін қолжетімді командалар**\n"
    
    if role == 'user':
        help_text += user_commands + common_commands
    elif role == 'admin':
        help_text +=  admin_commands + common_commands
    elif role == 'superadmin':
        help_text +=  superadmin_commands + common_commands
    
    help_text += """
📝 **Мысалдар:**
/user_info 1
/item_info 1
/list_items
"""
    
    await message.reply(help_text)

@router.message(F.text & ~F.text.startswith('/'))
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})

    # Алдымен тауар құру/жаңартуды өңдеу
    if state.get("creating_item"):
        await handle_item_creation(message)
        return
    
    # Бірінші категория құруды өңдеу
    if state.get("creating_category"):
        await handle_category_creation(message)
        return
    
    # Пайдаланушы құруды өңдеу
    if state.get("creating_user"):
        await handle_user_creation(message)
        return
    
    # Пайдаланушы жаңартуды өңдеу (егер интерактивті әдіс қолданылса)
    if state.get("updating_user"):
        await handle_user_update(message)
        return

    if state.get("updating_item"):
        await handle_item_update(message)
        return

    # Кіруді өңдеу - /start командасынан кейін ғана
    if state.get("waiting_for_login") and not state.get("is_logged_in", False):
        parts = message.text.split()
        
        if len(parts) == 2:
            username, password = parts[0], parts[1]
            
            try:
                # Token негізінде кіру
                response, status_code = await api_client.login(username, password)
                
                if status_code == 200 and response.get('success'):
                    # ✅ МАҢЫЗДЫ: Token-ді api_client-те сақтау
                    api_client.token = response.get('token')
                    
                    # Сәтті кіру
                    user_data = response['user']
                    user_login_state[user_id] = {
                        "is_logged_in": True,
                        "username": username,
                        "user_id": user_data['id'],
                        "role": user_data['role'],
                        "waiting_for_login": False
                    }
                    
                    await message.reply(f"✅ Қош келдіңіз, {username}! Сіз жүйеге {user_data['role']} ретінде сәтті кірдіңіз.")
                    await show_available_commands(message, user_data['role'])
                    return
                else:
                    error_msg = response.get('error', 'Қате деректер')
                    await message.reply(f"❌ Кіру қатесі: {error_msg}\nҚайталап көріңіз немесе қайта кіру үшін /start қолданыңыз.")
                    return
                    
            except Exception as e:
                logging.error(f"Кіру қатесі: {e}")
                await message.reply("❌ Серверге қосылу кезінде қате пайда болды. Django серверінің жұмыс істеп тұрғанын тексеріңіз.")
                return
        else:
            await message.reply("🔐 Логин мен парольді бос орын арқылы енгізіңіз.\nМысалы: `username password`\nНемесе қайта кіру үшін /start қолданыңыз.", parse_mode='Markdown')
            return
        
    # Егер жүйеге кірген болса, бірақ кездейсоқ мәтін жіберсе
    if state.get("is_logged_in", False):
        await message.reply("ℹ️ Қолжетімді командаларды көру үшін /help қолданыңыз.")
        return
    
    # Егер жүйеге кірмеген болса және кіру күтілмесе
    await message.reply("🔐 Жүйеге кіру үшін /start қолданыңыз.")

@router.message(Command("create_user"))
async def create_user_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    # Рұқсатты тексеру (тек superadmin)
    if state.get('role') != 'superadmin':
        await message.reply("❌ Пайдаланушы құру құқығыңыз жоқ. superadmin рөлі қажет.")
        return
    
    instructions = """
👤 **Жаңа пайдаланушы құру**

Пайдаланушы деректерін келесі форматта жіберіңіз:
username: пайдаланушы_аты
email: email@example.com
password: пароль
role: user/admin/superadmin

**Мысалы:**
username: TairkhanWhyJava
email: tair@example.com
password: safe_password123
role: user

*`username`, `email` және `password` өрістері міндетті!*
*Әдепкі рөл: `user`*
"""
    await message.reply(instructions)
    
    # Пайдаланушы құру күйін орнату
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
                        await message.reply("❌ Қате: рөл 'user', 'admin' немесе 'superadmin' болуы керек")
                        user_login_state[user_id]["creating_user"] = False
                        return
        
        # Міндетті өрістерді тексеру
        for field in required_fields:
            if field not in user_data:
                missing_fields.append(field)
        
        if missing_fields:
            await message.reply(f"❌ Міндетті өрістер жоқ: {', '.join(missing_fields)}")
            user_login_state[user_id]["creating_user"] = False
            return
        
        # Егер рөл көрсетілмесе, әдепкі рөлді орнату
        if 'role' not in user_data:
            user_data['role'] = 'user'
        
        # API арқылы пайдаланушы құру
        response, status_code = await api_client.create_user(user_data)
        
        if status_code == 201:
            await message.reply(f"✅ '{user_data['username']}' пайдаланушысы сәтті құрылды!")
            
            user_info = f"""
👤 **Жаңа пайдаланушы құрылды:**

🆔 Пайдаланушы аты: {user_data['username']}
📧 Email: {user_data['email']}
🎭 Рөл: {user_data['role']}
"""
            await message.reply(user_info)
        elif status_code == 400:
            if isinstance(response, dict):
                if 'username' in response:
                    await message.reply(f"❌ '{user_data['username']}' пайдаланушы аты бос емес!")
                elif 'email' in response:
                    await message.reply(f"❌ '{user_data['email']}' email мекенжайы бос емес!")
                else:
                    await message.reply(f"❌ Пайдаланушыны құру кезінде қате: {response}")
            else:
                await message.reply(f"❌ Пайдаланушыны құру кезінде қате: {response}")
        else:
            await message.reply(f"❌ API қатесі: статус {status_code}, жауап: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Күтпеген қате пайда болды: {str(e)}")
    
    # Құру күйін тазалау
    user_login_state[user_id]["creating_user"] = False

@router.message(Command("list_users"))
async def list_users(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return

    if state.get('role') != 'superadmin':
        await message.reply("❌ Пайдаланушылар тізімін көру құқығыңыз жоқ. superadmin рөлі қажет.")
        return
    
    try:
        response, status_code = await api_client.get_users()
        
        if status_code == 200 and response:
            users_list = "\n".join([f"👤 {user['id']}: {user['username']} ({user['email']}) - {user.get('role', 'user')}" 
                                  for user in response])
            await message.reply(f"📋 Пайдаланушылар тізімі:\n{users_list}")
        elif status_code == 200 and not response:
            await message.reply("ℹ️ Тіркелген пайдаланушылар жоқ.")
        else:
            await message.reply(f"❌ Пайдаланушылар тізімін алу кезінде қате: статус {status_code}, жауап: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {e}")

@router.message(Command("user_info"))
async def user_info(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Қолданылуы: /user_info <пайдаланушы_id>")
            return
        
        user_id_param = parts[1]
        response, status_code = await api_client.get_user(user_id_param)
        
        if status_code == 200:
            user = response
            user_info_lines = [
                "👤 Пайдаланушы туралы ақпарат:",
                f"🆔 ID: {user.get('id', 'N/A')}",
                f"👤 Пайдаланушы аты: {user.get('username', 'N/A')}",
                f"📧 Email: {user.get('email', 'N/A')}",
                f"🎭 Рөл: {user.get('role', 'user')}",
                f"✅ Белсенді: {'Иә' if user.get('is_active', True) else 'Жоқ'}"
            ]
            
            await message.reply("\n".join(user_info_lines))
            
        elif status_code == 404:
            await message.reply(f"❌ {user_id_param} ID пайдаланушысы табылмады.")
        else:
            await message.reply(f"❌ Қате: статус {status_code}, жауап: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {str(e)}")

@router.message(Command("update_user"))
async def update_user_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Қолданылуы: /update_user <пайдаланушы_id>")
            return
        
        user_id_param = parts[1]
        
        # Алдымен пайдаланушының бар екенін тексеру
        response, status_code = await api_client.get_user(user_id_param)
        if status_code != 200:
            await message.reply(f"❌ {user_id_param} ID пайдаланушысы табылмады.")
            return

        instructions = f"""
👤 **{user_id_param} ID пайдаланушыны жаңарту**

Жаңарту деректерін келесі форматта жіберіңіз:
username: Жаңа пайдаланушы аты
email: Жаңа email
password: Жаңа пароль

**Тек жаңартқыңыз келетін өрістерді ғана жіберіңіз.**

📝 **Мысалы:**
username: AYALUBLU
email: ayalublu@gmail.com
password: newsecurepassword123
"""
        await message.reply(instructions)
        
        user_login_state[user_id]["updating_user"] = True
        user_login_state[user_id]["updating_user_id"] = user_id_param
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {e}")

async def handle_user_update(message: types.Message):
    user_id = message.from_user.id
    try:
        user_id_param = user_login_state[user_id].get("updating_user_id")
        
        if not user_id_param:
            await message.reply("❌ Қате: Пайдаланушы ID табылмады")
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
            await message.reply("❌ Жаңарту үшін деректер көрсетілмеген")
            user_login_state[user_id]["updating_user"] = False
            return
        
        response, status_code = await api_client.update_user(user_id_param, user_data)
        
        if status_code == 200:
            updated_fields = []
            if 'username' in user_data:
                updated_fields.append(f"👤 Пайдаланушы аты: {user_data['username']}")
            if 'email' in user_data:
                updated_fields.append(f"📧 Email: {user_data['email']}")
            if 'password' in user_data:
                updated_fields.append("🔑 Пароль: жаңартылды")
            
            response_text = f"✅ {user_id_param} ID пайдаланушы сәтті жаңартылды!\n"
            if updated_fields:
                response_text += "\n".join(updated_fields)
            
            await message.reply(response_text)
            
        elif status_code == 404:
            await message.reply(f"❌ {user_id_param} ID пайдаланушысы табылмады")
        else:
            error_msg = f"Қате: {response}" if response else "Белгісіз қате"
            await message.reply(f"❌ Пайдаланушыны жаңарту кезінде қате: {error_msg}")
        
    except Exception as e:
        await message.reply(f"❌ Күтпеген қате пайда болды: {str(e)}")
    
    user_login_state[user_id]["updating_user"] = False
    user_login_state[user_id]["updating_user_id"] = None

@router.message(Command("delete_user"))
async def delete_user(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Қолданылуы: /delete_user <пайдаланушы_id>")
            return
        
        user_id_param = parts[1]
        response, status_code = await api_client.delete_user(user_id_param)
        
        if status_code == 204:
            await message.reply(f"✅ {user_id_param} ID пайдаланушы сәтті жойылды.")
        elif status_code == 404:
            await message.reply(f"❌ {user_id_param} ID пайдаланушысы табылмады.")
        else:
            await message.reply(f"❌ Пайдаланушыны жою кезінде қате: статус {status_code}, жауап: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {e}")

@router.message(Command("list_items"))
async def list_items_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    try:
        response, status_code = await api_client.get_items()
        
        if status_code == 200 and response:
            items_list = []
            for item in response:
                # Категориялар туралы ақпаратты қалыптастыру
                categories_info = ""
                if item.get('categories'):
                    category_names = [cat['name'] for cat in item['categories']]
                    categories_info = f" | 📁 {', '.join(category_names)}"
                
                items_list.append(f"🛍️ {item['id']}: {item['name']} - 💰 {item['price']} ₸{categories_info}")
            
            items_text = "\n".join(items_list)
            await message.reply(f"📋 Тауарлар тізімі:\n{items_text}")
        elif status_code == 200 and not response:
            await message.reply("ℹ️ Дерекқорда тауарлар жоқ.")
        else:
            await message.reply(f"❌ Тауарлар тізімін алу кезінде қате: статус {status_code}, жауап: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {e}")


@router.message(Command("item_info"))
async def item_info_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Қолданылуы: /item_info <тауар_id>")
            return
        
        item_id = parts[1]
        response, status_code = await api_client.get_item(item_id)
        
        if status_code == 200:
            item = response
            item_info_lines = [
                "🛍️ Тауар туралы ақпарат:",
                f"🆔 ID: {item.get('id', 'N/A')}",
                f"📝 Атауы: {item.get('name', 'N/A')}",
                f"🔗 Slug: {item.get('slug', 'N/A')}",
                f"📋 Сипаттамасы: {item.get('description', 'Көрсетілмеген')}",
                f"💰 Бағасы: {item.get('price', 0)} ₸",
                f"✅ Қолжетімді: {'Иә' if item.get('available', True) else 'Жоқ'}"
            ]
            
            # Категориялар туралы ақпаратты қосу
            if item.get('categories'):
                category_names = [f"{cat['name']} (ID: {cat['id']})" for cat in item['categories']]
                item_info_lines.append(f"📁 Категориялар: {', '.join(category_names)}")
            else:
                item_info_lines.append("📁 Категориялар: Көрсетілмеген")
            
            await message.reply("\n".join(item_info_lines))
            
        elif status_code == 404:
            await message.reply(f"❌ {item_id} ID тауар табылмады.")
        else:
            await message.reply(f"❌ Қате: статус {status_code}, жауап: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {str(e)}")

@router.message(Command("create_item"))
async def create_item_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    try:
        instructions = """
📝 **Жаңа тауар құру**

Деректерді келесі форматта жіберіңіз:
name: Тауар атауы
slug: бірегей-слаг
description: Тауар сипаттамасы
price: 99.99
available: true
category_ids: 1,2,3

**Мысалы:**
name: iPhone 15
slug: iphone-15
description: Жақсартылған камерасы бар жаңа iPhone 15
price: 799.99
available: true
category_ids: 1,2,3

*`name` және `slug` өрістері міндетті!*
*`category_ids` - үтір арқылы бөлінген категория ID'лері (міндетті емес)*

📋 **Алдымен категориялар тізімін қараңыз:**
**Категориялар бар тізімнен болуы керек!**
/list_categories
"""
        await message.reply(instructions)
        
        user_login_state[user_id]["creating_item"] = True
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {e}")

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
                        await message.reply("❌ Қате: slug тек латын әріптері, сандар және дефис қамтуы мүмкін!")
                        return
                    item_data['slug'] = slug
                elif key == 'description':
                    item_data['description'] = value
                elif key == 'price':
                    try:
                        item_data['price'] = float(value)
                    except ValueError:
                        await message.reply("❌ Қате: баға сан болуы керек (мысалы: 99.99)")
                        return
                elif key == 'available':
                    item_data['available'] = value.lower() in ['true', 'yes', 'иә', '1', 'on']
                elif key == 'category_ids':
                    try:
                        # Категориялардың бар екенін тексеру
                        categories_response, status = await api_client.get_categories()
                        if status != 200:
                            await message.reply("❌ Қате: категориялар тізімін алу мүмкін болмады")
                            return
                        
                        existing_categories = [str(cat['id']) for cat in categories_response]
                        category_ids = [cat_id.strip() for cat_id in value.split(',')]
                        
                        # Әрбір категорияны тексеру
                        invalid_categories = []
                        for cat_id in category_ids:
                            if cat_id not in existing_categories:
                                invalid_categories.append(cat_id)
                        
                        if invalid_categories:
                            await message.reply(f"❌ Қате: келесі категориялар жоқ: {', '.join(invalid_categories)}")
                            return
                        
                        item_data['category_ids'] = [int(cat_id) for cat_id in category_ids]
                    except Exception as e:
                        await message.reply(f"❌ category_ids форматында қате: {e}")
                        return
        
        # Міндетті өрістерді тексеру
        required_fields = ['name', 'slug', 'price']
        for field in required_fields:
            if field not in item_data:
                await message.reply(f"❌ Міндетті '{field}' өрісі жоқ")
                return
        
        response, status_code = await api_client.create_item(item_data)
        
        if status_code == 201:
            await message.reply("✅ Тауар сәтті құрылды! 🎉")
            
            # Құрылған тауарды көрсету
            item_info = [
                f"📦 **Құрылған тауар:**",
                f"• Атауы: {item_data['name']}",
                f"• Slug: {item_data['slug']}",
                f"• Сипаттамасы: {item_data.get('description', 'Көрсетілмеген')}",
                f"• Бағасы: {item_data['price']} ₸",
                f"• Қолжетімді: {'Иә' if item_data.get('available', True) else 'Жоқ'}",
                f"• Категориялар: {item_data.get('category_ids', [])}"
            ]
            await message.reply("\n".join(item_info))
            
        else:
            error_msg = f"Қате: {response}" if response else "Белгісіз қате"
            await message.reply(f"❌ Тауарды құру кезінде қате: {error_msg}")
        
    except Exception as e:
        await message.reply(f"❌ Күтпеген қате пайда болды: {str(e)}")
    
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

        await message.reply(f"Сурет қабылданды және {file_name} ретінде сақталды. Енді тауар деректерін жіберіңіз.")

    except Exception as e:
        await message.reply(f"❌ Суретті өңдеу кезінде қате пайда болды: {e}")


@router.message(Command("update_item"))
async def update_item_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Қолданылуы: /update_item <тауар_id>")
            return
        
        item_id = parts[1]
        
        # Тауардың бар екенін тексеру
        response, status_code = await api_client.get_item(item_id)
        if status_code != 200:
            await message.reply(f"❌ {item_id} ID тауар табылмады.")
            return

        # Анықтама үшін категориялар тізімін алу
        categories_response, status = await api_client.get_categories()
        if status == 200:
            categories_info = "\n".join([f"  - {cat['id']}: {cat['name']}" for cat in categories_response])
            categories_text = f"\n📋 **Бар категориялар:**\n{categories_info}"
        else:
            categories_text = ""

        instructions = f"""
📝 **{item_id} ID тауарды жаңарту**

Жаңарту деректерін келесі форматта жіберіңіз:
name: Атауы
slug: слаг
description: Сипаттамасы
price: 149.99
available: false
category_ids: 1,2,3
{categories_text}

**Тек жаңартқыңыз келетін өрістерді ғана жіберіңіз.**
**category_ids үшін тек бар категория ID'лерін қолданыңыз!**
"""
        await message.reply(instructions)
        
        user_login_state[user_id]["updating_item"] = True
        user_login_state[user_id]["updating_item_id"] = item_id
        
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {e}")



async def handle_item_update(message: types.Message):
    user_id = message.from_user.id
    try:
        item_id = user_login_state[user_id].get("updating_item_id")
        
        if not item_id:
            await message.reply("❌ Қате: Тауар ID табылмады")
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
                        await message.reply("❌ Қате: slug тек латын әріптері, сандар және дефис қамтуы мүмкін!")
                        return
                    item_data['slug'] = slug
                elif key == 'description':
                    item_data['description'] = value
                elif key == 'price':
                    try:
                        item_data['price'] = float(value)
                    except ValueError:
                        await message.reply("❌ Қате: баға сан болуы керек (мысалы: 99.99)")
                        return
                elif key == 'available':
                    item_data['available'] = value.lower() in ['true', 'yes', 'иә', '1', 'on']
                elif key == 'category_ids':
                    try:
                        # Категориялардың бар екенін тексеру
                        categories_response, status = await api_client.get_categories()
                        if status != 200:
                            await message.reply("❌ Қате: категориялар тізімін алу мүмкін болмады")
                            return
                        
                        existing_categories = [str(cat['id']) for cat in categories_response]
                        category_ids = [cat_id.strip() for cat_id in value.split(',')]
                        
                        # Әрбір категорияны тексеру
                        invalid_categories = []
                        for cat_id in category_ids:
                            if cat_id not in existing_categories:
                                invalid_categories.append(cat_id)
                        
                        if invalid_categories:
                            await message.reply(f"❌ Қате: келесі категориялар жоқ: {', '.join(invalid_categories)}")
                            return
                        
                        item_data['category_ids'] = [int(cat_id) for cat_id in category_ids]
                    except Exception as e:
                        await message.reply(f"❌ category_ids форматында қате: {e}")
                        return
                        
        if not item_data:
            await message.reply("❌ Жаңарту үшін деректер көрсетілмеген")
            user_login_state[user_id]["updating_item"] = False
            return
        
        response, status_code = await api_client.update_item(item_id, item_data)
        
        if status_code == 200:
            await message.reply(f"✅ {item_id} ID тауар сәтті жаңартылды! 🎉")
            
            updated_info = ["🔄 Жаңартылған өрістер:"]
            for key, value in item_data.items():
                if key == 'available':
                    value = 'Иә' if value else 'Жоқ'
                elif key == 'price':
                    value = f"{value} ₸"
                updated_info.append(f"• {key}: {value}")
            
            await message.reply("\n".join(updated_info))
            
        elif status_code == 404:
            await message.reply(f"❌ {item_id} ID тауар табылмады")
        else:
            error_msg = f"Қате: {response}" if response else "Белгісіз қате"
            await message.reply(f"❌ Тауарды жаңарту кезінде қате: {error_msg}")
        
    except Exception as e:
        await message.reply(f"❌ Күтпеген қате пайда болды: {str(e)}")
    
    user_login_state[user_id]["updating_item"] = False
    user_login_state[user_id]["updating_item_id"] = None

@router.message(Command("delete_item"))
async def delete_item_command(message: types.Message):
    user_id = message.from_user.id
    if not user_login_state.get(user_id, {}).get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Қолданылуы: /delete_item <тауар_id>")
            return
        
        item_id = parts[1]
        response, status_code = await api_client.delete_item(item_id)
        
        if status_code == 204:
            await message.reply(f"✅ {item_id} ID тауар сәтті жойылды.")
        elif status_code == 404:
            await message.reply(f"❌ {item_id} ID тауар табылмады.")
        else:
            await message.reply(f"❌ Тауарды жою кезінде қате: статус {status_code}, жауап: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {e}")

# ========== ТАПСЫРЫС КОМАНДАЛАРЫ ==========
@router.message(Command("buy_item"))
async def buy_item_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("ℹ️ Қолданылуы: /buy_item <тауар_id> [саны]\nМысалы: /buy_item 1 2")
            return
        
        item_id = parts[1]
        quantity = int(parts[2]) if len(parts) > 2 else 1
        
        # Тапсырыс деректерін құру
        order_data = {
            "item": item_id,
            "quantity": quantity
        }
        
        response, status_code = await api_client.create_order(order_data)
        
        if status_code == 201:
            await message.reply(f"✅ Сатып алу сәтті ресімделді! 🎉")
            
            order_info = f"""
🧾 **Тапсырыс мәліметтері:**

🆔 Тапсырыс ID: {response.get('id')}
📦 Тауар: {response.get('item_name')}
💰 Бірлік бағасы: {response.get('item_price')} ₸
📊 Саны: {response.get('quantity')}
💵 Барлығы: {response.get('total_price')} ₸
📅 Күні: {response.get('created_at', '')[:16]}
"""
            await message.reply(order_info)
        elif status_code == 404:
            await message.reply("❌ Тауар табылмады.")
        else:
            await message.reply(f"❌ Сатып алу кезінде қате: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {str(e)}")

@router.message(Command("my_orders"))
async def my_orders_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    try:
        response, status_code = await api_client.get_orders()
        
        if status_code == 200 and response:
            orders_text = "📋 **Сіздің тапсырыстарыңыздың тарихы:**\n\n"
            
            for order in response:
                orders_text += f"""
🧾 **Тапсырыс #{order['id']}**
📦 Тауар: {order.get('item_name', 'N/A')}
💰 Бағасы: {order.get('total_price')} ₸
📊 Саны: {order.get('quantity')}
📅 Күні: {order.get('created_at', '')[:16]}
📊 Мәртебесі: {order.get('status', 'N/A')}
────────────────────
"""
            await message.reply(orders_text)
        elif status_code == 200 and not response:
            await message.reply("ℹ️ Сізде әлі тапсырыстар жоқ.")
        else:
            await message.reply(f"❌ Тапсырыстарды алу кезінде қате: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {str(e)}")

@router.message(Command("list_orders"))
async def list_orders_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    # Рұқсатты тексеру (тек admin/superadmin)
    if state.get('role') not in ['admin', 'superadmin']:
        await message.reply("❌ Барлық тапсырыстарды көру құқығыңыз жоқ. admin рөлі қажет.")
        return
    
    try:
        response, status_code = await api_client.get_orders()
        
        if status_code == 200 and response:
            orders_text = "📋 **Жүйедегі барлық тапсырыстар:**\n\n"
            
            for order in response:
                orders_text += f"""
🧾 **Тапсырыс #{order['id']}**
👤 Пайдаланушы ID: {order.get('user', 'N/A')}
📦 Тауар: {order.get('item_name', 'N/A')}
💰 Сомасы: {order.get('total_price')} ₸
📊 Саны: {order.get('quantity')}
📅 Күні: {order.get('created_at', '')[:16]}
📊 Мәртебесі: {order.get('status', 'N/A')}
────────────────────
"""
            await message.reply(orders_text)
        elif status_code == 200 and not response:
            await message.reply("ℹ️ Жүйеде әлі тапсырыстар жоқ.")
        else:
            await message.reply(f"❌ Тапсырыстарды алу кезінде қате: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {str(e)}")

# ========== КАТЕГОРИЯ КОМАНДАЛАРЫ ==========
@router.message(Command("create_category"))
async def create_category_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    # Рұқсатты тексеру (тек admin)
    if state.get('role') not in ['admin', 'superadmin']:
        await message.reply("❌ Категория құру құқығыңыз жоқ. admin рөлі қажет.")
        return
    
    instructions = """
📁 **Жаңа категория құру**

Категория деректерін келесі форматта жіберіңіз:
name: Категория атауы
title: Категория сипаттамасы
slug: бірегей-слаг

**Мысалы:**
name: Носки
title: Әртүрлі шұлық түрлері
slug: socks

*`name` және `slug` өрістері міндетті!*
"""
    await message.reply(instructions)
    
    # Категория құру күйін орнату
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
                        await message.reply("❌ Қате: slug тек латын әріптері, сандар және дефис қамтуы мүмкін!")
                        user_login_state[user_id]["creating_category"] = False
                        return
                    category_data['slug'] = slug
        
        for field in required_fields:
            if field not in category_data:
                missing_fields.append(field)
        
        if missing_fields:
            await message.reply(f"❌ Міндетті өрістер жоқ: {', '.join(missing_fields)}")
            user_login_state[user_id]["creating_category"] = False
            return
        
        # API арқылы категория құру
        response, status_code = await api_client.create_category(category_data)
        
        if status_code == 201:
            await message.reply(f"✅ '{category_data['name']}' категориясы сәтті құрылды!")
            
            category_info = f"""
📁 **Жаңа категория құрылды:**

📝 Атауы: {category_data['name']}
📋 Сипаттамасы: {category_data.get('title', 'Көрсетілмеген')}
🔗 Slug: {category_data['slug']}
"""
            await message.reply(category_info)
        else:
            await message.reply(f"❌ Категорияны құру кезінде қате: статус {status_code}, жауап: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Күтпеген қате пайда болды: {str(e)}")
    
    user_login_state[user_id]["creating_category"] = False

@router.message(Command("list_categories"))
async def list_categories_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if not state.get("is_logged_in"):
        await message.reply("❌ Алдымен /start арқылы жүйеге кіріңіз")
        return
    
    try:
        response, status_code = await api_client.get_categories()
        
        if status_code == 200 and response:
            categories_list = "\n".join([f"📁 {cat['id']}: {cat['name']} - {cat.get('title', '')}" 
                                       for cat in response])
            await message.reply(f"📋 Категориялар тізімі:\n{categories_list}")
        elif status_code == 200 and not response:
            await message.reply("ℹ️ Дерекқорда категориялар жоқ.")
        else:
            await message.reply(f"❌ Категориялар тізімін алу кезінде қате: статус {status_code}, жауап: {response}")
            
    except Exception as e:
        await message.reply(f"❌ Қате пайда болды: {e}")

@router.message(Command("help"))
async def send_help_command(message: types.Message):
    user_id = message.from_user.id
    state = user_login_state.get(user_id, {})
    
    if state.get("is_logged_in"):
        # ✅ Пайдаланушының рөлін алып, show_available_commands функциясына жіберу
        role = state.get('role', 'user')
        await show_available_commands(message, role)
    else:
        await message.reply("ℹ️ Алдымен /start арқылы жүйеге кіріңіз")

@router.message(Command("logout"))
async def logout_command(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_login_state:
        username = user_login_state[user_id].get('username', '')
        user_login_state[user_id] = {"is_logged_in": False, "waiting_for_login": False}
        api_client.token = None  # ✅ Token-ді тазалау
        await message.reply(f"✅ {username}, сіз жүйеден шықтыңыз. Кіру үшін /start қолданыңыз.")
    else:
        await message.reply("ℹ️ Сіз авторизациядан өтпегенсіз.")


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    print("🤖 Бот іске қосылуда...")
    print("✅ Бот дайын!")
    print("🔗 Django серверінің http://localhost:8000 мекенжайында жұмыс істеп тұрғанын тексеріңіз")
    print("🚀 Telegram-да бастау үшін /start қолданыңыз")
    print(f"🔐 Әдепкі деректер: {DEFAULT_USERNAME} / {DEFAULT_PASSWORD}")
    asyncio.run(main())