# Импорты
import os
import sys
import json
import telebot
from telebot.types import TransactionPartner
#from background import keep_alive #импорт функции для поддержки работоспособности
import pip
pip.main(['install', 'pytelegrambotapi'])
import time
import sqlite3
import threading
import datetime
import random
lock = threading.Lock()

SCRIPT_PATH = f'{os.path.dirname(os.path.abspath(__file__))}'

#Получение данных из json
with open(f'{SCRIPT_PATH}/const.json', 'r', encoding='utf-8') as file:
  constants = json.load(file)
with open(f'{SCRIPT_PATH}/tokens.json', 'r', encoding='utf-8') as file:
  tokens = json.load(file)
with open(f'{SCRIPT_PATH}/admins.json', 'r', encoding='utf-8') as file:
  ADMIN_LIST = json.load(file)['admin_usernames']

#Константы
TRANSACTION_LIMIT = constants['TRANSACTION_LIMIT'] # Максимальное количество Ничего в транзакции
HISTORY_LENGTH = constants['HISTORY_LENGTH'] # Максимальная длина вывода статистики
NOTHING_DEFAULT_MIN = constants['NOTHING_DEFAULT_MIN'] # Минимальное количество получаемых Ничего по умолчанию
NOTHING_DEFAULT_MAX = constants['NOTHING_DEFAULT_MAX'] # Максимальное количество получаемых Ничего по умолчанию
NOTHING_LOW_LIMIT = constants['NOTHING_LOW_LIMIT'] # Минимальное количество Ничего у пользователя
NOTHING_HIGH_LIMIT = constants['NOTHING_HIGH_LIMIT'] # Максимальное количество Ничего у пользователя
KEYBOARD_GIVE_USER_MAXLEN = constants['KEYBOARD_GIVE_USER_MAXLEN'] # Максимальное количество пользователей в команде /give
KEYBOARD_GIVE_USER_WIDTH = constants['KEYBOARD_GIVE_USER_WIDTH'] # Ширина клавиатуры при выборе пользователя в /give
KEYBOARD_GIVE_NOTHING_MIN = constants['KEYBOARD_GIVE_NOTHING_MIN'] # Минимальное количество Ничего в /give
KEYBOARD_GIVE_NOTHING_MAX = constants['KEYBOARD_GIVE_NOTHING_MAX'] # Максимальное количество Ничего в /give
KEYBOARD_GIVE_NOTHING_WIDTH = constants['KEYBOARD_GIVE_NOTHING_WIDTH'] # Ширина клавиатуры при выборе количества ничего в /give

####################################################################################################
#Выбор режима работы (тест/релиз)
print("Hello! Checking the system parameter for work mode\n")
print(sys.argv)
try:
  if sys.argv[1] == 'RELEASE':
    BOT_TOKEN = tokens['BOT_RELEASE_TOKEN']
    print("WARNING: RUNNING THE RELEASE MODE!")
    database_name = 'ntc_database.db'
  else:
    BOT_TOKEN = tokens['BOT_TEST_TOKEN']
    print("SUCCESS: running the TESTING mode")
    database_name = 'ntc_database_test.db'
except IndexError:
  BOT_TOKEN = tokens['BOT_TEST_TOKEN']
  print("SUCCESS: running the TESTING mode")
  database_name = 'ntc_database_test.db'

####################################################################################################
# Создание бота
bot = telebot.TeleBot(BOT_TOKEN)
print(f'SUCCESS: Bot created!')
# Подключение к базе данных пользователей SQLite
if not os.path.exists(f"{SCRIPT_PATH}/{database_name}"):
    open(f"{SCRIPT_PATH}/{database_name}", "w")
    print("SUCCESS: New database file is created!")
else:
    print("SUCCESS: Database file is found!")
database = sqlite3.connect(f"{SCRIPT_PATH}/{database_name}", check_same_thread=False)
cursor = database.cursor()
# Создание БД пользователей, если она не существует
cursor.execute('''CREATE TABLE IF NOT EXISTS 
users (
id INTEGER PRIMARY KEY,
username TEXT,
balance INTEGER DEFAULT 0
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS 
transactions (
date TEXT PRIMARY KEY,
user_id_giver INTEGER,
user_id_taker INTEGER,
nothing_amount INTEGER
)''')
database.commit()
print(f'SUCCESS: Database is connected!')

####################################################################################################
#Класс пользователей
class User:
  def __init__(self, id:int = None, username:str = '', balance:int = None):
    self.id = id
    self.username = username
    self.balance = balance
  # Метод проверки на админа
  def check_admin(self):
    for admin in ADMIN_LIST:
      if admin.lower() == self.username.lower():
        print('SUCCESS: Access granted')
        return (True)
    print('ERROR: Access denied')
    return(False)
  #Метод по получению всех транзакций пользователя
  def get_transactions(self):
    transactions = []
    with lock:
      cursor.execute("SELECT * FROM transactions WHERE user_id_giver = ? OR user_id_taker = ?",(self.id,self.id))
      transactions_fetch = cursor.fetchall()
    if transactions_fetch is None: 
      print('ERROR: Empty transactions database')
      return(None)
    for transaction_fetch in transactions_fetch:
      transactions.append(Transaction(get_user(transaction_fetch[1]),get_user(transaction_fetch[2]),transaction_fetch[3],transaction_fetch[0])) 
    return(transactions) 

#Функция присвоения юзера
def get_user(user_data):
  #print(f"NOTE: Start user get by data:{user_data}")
  if user_data is None:
    print("ERROR: missing user data!")
    return(None)
  with lock:
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_data,))
    user_fetch = cursor.fetchone()
  print(user_fetch)
  if user_fetch is None:
    with lock:
      cursor.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (user_data,))
      user_fetch = cursor.fetchone()
  if user_fetch is None:
      print("ERROR: missing user!")
      return(None)
  user = User(user_fetch[0],user_fetch[1],user_fetch[2])
  return(user)
 
#Функция присвоения полного списка юзеров
def get_users_all():
  users = []
  with lock:
    cursor.execute("SELECT * FROM users")
    users_fetch = cursor.fetchall()
  if users_fetch is None: 
    print('ERROR: Empty users database')
    return(None)
  for user_fetch in users_fetch:
    users.append(User(user_fetch[0],user_fetch[1],user_fetch[2]))
  return(users) 

#Класс транзакций
class Transaction:
  def __init__(self, user_giver:User = User(), user_taker:User = User(), amount:int = None, date=datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=3))).strftime("%d.%m.%Y %H:%M:%S")):
    self.user_giver = user_giver
    self.user_taker = user_taker
    self.amount = amount
    self.date = date 
  #Метод осуществления передачи
  def transaction(self, chat_id):
    self.date: str = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=3))).strftime("%d.%m.%Y %H:%M:%S")
    with lock:
      cursor.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (self.amount, self.user_giver.id))
      cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (self.amount, self.user_taker.id))
      database.commit()
    self.user_giver.balance -= self.amount
    self.user_taker.balance += self.amount
    with lock:
      cursor.execute("INSERT INTO transactions (date, user_id_giver, user_id_taker, nothing_amount) VALUES (?, ?, ?, ?)", (self.date, self.user_giver.id, self.user_taker.id, self.amount))
      database.commit()
    print("SUCCESS: Nothing is given")
    if self.user_giver.id != user_bot.id:
      bot.send_message(chat_id, f"@{self.user_giver.username} передал @{self.user_taker.username} {self.amount} Ничего!")
    else:
      bot.send_message(chat_id, f"Биржа начислила @{self.user_taker.username} {self.amount} Ничего!")
    try:
      member = bot.get_chat_member(chat_id=chat_id, user_id=self.user_taker.id)
      print("chatmember")
    except telebot.apihelper.ApiException as e:
      if self.user_giver.id != user_bot.id:
        bot.send_message(self.user_taker.id, f"Пользователь @{self.user_giver.username} передал Вам {self.amount} Ничего!\n\nВаш баланс: {self.user_taker.balance} Ничего.")
      else:
        bot.send_message(self.user_taker.id, f"Биржа начислила Вам {self.amount} Ничего!\n\nВаш баланс: {self.user_taker.balance} Ничего.")
      print("notachatmember")
      print_user_db()
  # Проверка транзакции
  def check_transaction(self, chat_id):
    if NOTHING_HIGH_LIMIT is not None:
      if NOTHING_HIGH_LIMIT < self.user_taker.balance + self.amount:
        print("ERROR: Taker balance overflow")
        bot.send_message(chat_id, f"У получателя @{self.user_taker.username} станет слишком много ничего!\nПопробуйте отправить поменьше.")
        return(False)
      if NOTHING_HIGH_LIMIT < self.user_giver.balance - self.amount:
        print("ERROR: Giver balance overflow")
        bot.send_message(chat_id, f"У отправителя @{self.user_giver.username} станет слишком много ничего!\nПопробуйте отправить побольше.")
        return(False)
    if NOTHING_LOW_LIMIT is not None:
      if NOTHING_LOW_LIMIT > self.user_giver.balance - self.amount:
        print("ERROR: Giver balance underflow")
        bot.send_message(chat_id, f"У тебя нет столько ничего! Твой баланс {self.user_giver.balance} Ничего.\nПопроси у кого-нибудь еще!")
        return(False)
      if NOTHING_LOW_LIMIT > self.user_taker.balance + self.amount:
        print("ERROR: Taker balance underflow")
        bot.send_message(chat_id, f"У пользователя @{self.user_taker.username} станет слишком мало ничего!\nЕго баланс сейчас: {self.user_taker.balance} Ничего.")
        return(False)
    return(True)

#Функция по получению всех транзакций
def get_transactions_all():
  transactions = []
  with lock:
    cursor.execute("SELECT * FROM transactions")
    transactions_fetch = cursor.fetchall()
  if transactions_fetch is None: 
    print('ERROR: Empty transactions database')
    return(None)
  for transaction_fetch in transactions_fetch:
    transactions.append(Transaction(get_user(transaction_fetch[1]),get_user(transaction_fetch[2]),transaction_fetch[3],transaction_fetch[0])) 
  return(transactions) 

#Функция для вывода базы данных пользователей
def print_user_db():
  with lock:
    cursor.execute("SELECT * FROM users") # Выполнение запроса
    rows = cursor.fetchall() # Получение данных
  print("Printing database:\n id | username | balance ")
  for row in rows: # Вывод данных
    print(row)
  print("\n")

#Функция для вывода базы данных транзакций
def print_trans_db():
  with lock:
    cursor.execute("SELECT * FROM transactions") # Выполнение запроса
    rows = cursor.fetchall() # Получение данных
  print("Printing database:\n date | user_id_giver | user_id_taker | nothing_amount")
  for row in rows: # Вывод данных
    print(row)
  print("\n")

def print_message(message:telebot.types.Message):
   print(f'\n{message.from_user.username} says: {message.text}')
   
#####################################################################################################
#Блок Функций проверок

#Проверка наличия пользователя в базе
def check_user(user_data):
  print(f"NOTE: Start user check by data: {user_data}")
  user = get_user(user_data)
  if user is None:
    #bot.reply_to(message, f"@{username}: Пользователь не найден!")
    print("ERROR: User is not found")
    return(False)
  else:
    return(True)

#Проверка на количество Ничего
def check_amount(amount, chat_id):
  try:
    amount = int(amount)
  except ValueError:
    print("ERROR: Invalid amount")
    bot.send_message(chat_id, "Неверное количество Ничего!")
    return(False)
  #Проверка на нулевую передачу Ничего
  if amount == 0  :
    print("ERROR: Zero transaction")
    bot.send_message(chat_id, "Ха-ха, у нас тут Клоун. Вы не можете передать 0 Ничего!")
    return(False)
  #Проверка на отрицательную передачу Ничего
  if amount < 0  :
    print("ERROR: Negative transaction")
    bot.send_message(chat_id, "Ого, да Вы умны! Но к сожалению, Вы не можете передать отрицательное количество Ничего!")
    return(False)
  #Проверка на большое количество Ничего
  if amount > TRANSACTION_LIMIT:
    print("ERROR: Large transaction")
    bot.send_message(chat_id, f"Вы не можете передать больше {TRANSACTION_LIMIT} Ничего! Это Вам не деньги, чтобы их так тратить!")
    return(False)
  return(True)

def check_amount_admin(amount, chat_id):
  try:
    amount = int(amount)
  except ValueError:
    print("ERROR: Invalid amount")
    bot.send_message(chat_id, "Неверное количество Ничего!")
    return(False)
  return(True)

#Проверка получающего
def check_taker(user_taker:User,user_giver:User, chat_id):
  if user_taker is None:
    print("ERROR: Taker is not found")
    bot.send_message(chat_id, f"Получатель не найден!")
    return(False)
    #Проверка на отправление себе
  if user_giver.id == user_taker.id:
      print("ERROR: Giver is taker")
      bot.send_message(chat_id, "Ха-ха, очень смешно. Вы не можете отправить самому себе Ничего!")
      return(False)
  if user_taker.id == user_bot.id:
      print("ERROR: Taker is bot")
      bot.send_message(chat_id, "Увы, Вы не можете передать Ничего боту! Почему Вы вообще попробовали это сделать?")
      return(False)
  return(True)

#Проверка отправляющего сообщение
def check_sender(user_giver:User, chat_id):
  if user_giver is None:
    print("ERROR: Giver is not found")
    bot.send_message(chat_id, "Вы не зарегистрированы на бирже Ничего!\nЗарегистрируйтесь, чтобы начать обмениваться Ничем.")
    return(False)
  if user_giver.balance == NOTHING_LOW_LIMIT:
    print("ERROR: No nothing")
    bot.send_message(chat_id, "У вас закончилось ничего! Чтобы отдать ничего, сначала надо получить ничего.\nПопросите у кого-нибудь.")
    return(False)
  return(True)

####################################################################################################
#Проверка наличия Бота в БД (Для админских функций)
user_bot = User(int(BOT_TOKEN.split(':',1)[0]),bot.get_me().username, 0)
if check_user(user_bot.id) == False:
  with lock:
    cursor.execute("INSERT INTO users (id, username, balance) VALUES (?, ?, ?)", (user_bot.id, user_bot.username, user_bot.balance))
    database.commit()
    print(f'SUCCESS: Bot user is added!')

###################################################################################################
##                                      ГРАФИЧЕСКИЕ КОМАНДЫ                                      ##
###################################################################################################
user_selected = {}
# Словарь, где ключ — ID пользователя (чат), а значение — множество выбранных им чисел.
transactions_new = {}
# Словарь, где ключ — ID пользователя (чат), а значение — новая транзакция этого пользователя.
admin_transactions_new = {}

def keyboard_give_user(user_id, user_list, command):
  markup = telebot.types.InlineKeyboardMarkup(row_width=KEYBOARD_GIVE_USER_WIDTH )
  # selected = user_selected.get(user_id, None)
  buttons = []
  for userlist_id in user_list:
    user = get_user(userlist_id)
    buttons.append(telebot.types.InlineKeyboardButton(text=f"@{user.username}", callback_data=f"{user_id}_NTC_{command}_user_@{user.username}"))
    if len(buttons) == KEYBOARD_GIVE_USER_MAXLEN: break
  # Разбиваем кнопки по рядам
  rows = []
  total_buttons = len(buttons)
  for start in range(0, total_buttons, KEYBOARD_GIVE_USER_WIDTH ):
    row_buttons = buttons[start:start + KEYBOARD_GIVE_USER_WIDTH ]
    # Если последний ряд короче ширины — добавляем пустые кнопки в конец
    if len(row_buttons) < KEYBOARD_GIVE_USER_MAXLEN:
      empty_count = 0 # KEYBOARD_GIVE_USER_WIDTH - len(row_buttons)
      for _ in range(empty_count):
        # Пустая кнопка — текст пробел, callback_data="ignore"
        row_buttons.append(telebot.types.InlineKeyboardButton(text=" ", callback_data=f"{user_id}_NTC_ignore"))
    rows.append(row_buttons)
  # Добавляем все ряды в markup
  for row_buttons in rows:
      markup.row(*row_buttons)
  # Кнопка "Другой пользователь" в отдельном ряду
  markup.add(telebot.types.InlineKeyboardButton(text="Другой пользователь", callback_data=f"{user_id}_NTC_{command}_user_other"))
  return markup

def keyboard_give_amount(user_id, command):
  user = get_user(user_id)
  markup = telebot.types.InlineKeyboardMarkup(row_width=KEYBOARD_GIVE_NOTHING_WIDTH )
  # selected = user_selected.get(user_id, None)
  buttons = []
  if command == 'give': max_amount = min(KEYBOARD_GIVE_NOTHING_MAX, user.balance, TRANSACTION_LIMIT)
  elif command == 'balanceadd': max_amount = min(KEYBOARD_GIVE_NOTHING_MAX, user.balance, TRANSACTION_LIMIT)
  for i in range(KEYBOARD_GIVE_NOTHING_MIN, max_amount + 1):
    buttons.append(telebot.types.InlineKeyboardButton(text=f"{i}", callback_data=f"{user_id}_NTC_{command}_amount_{i}"))
  # Разбиваем кнопки по рядам
  rows = []
  total_buttons = len(buttons)
  for start in range(0, total_buttons, KEYBOARD_GIVE_NOTHING_WIDTH ):
    row_buttons = buttons[start:start + KEYBOARD_GIVE_NOTHING_WIDTH ]
    # Если последний ряд короче ширины — добавляем пустые кнопки в конец
    if len(row_buttons) < min(max_amount, user.balance):
      empty_count = KEYBOARD_GIVE_NOTHING_WIDTH - len(row_buttons)
      for _ in range(empty_count):
        # Пустая кнопка — текст пробел, callback_data="ignore"
        row_buttons.append(telebot.types.InlineKeyboardButton(text=" ", callback_data=f"{user_id}_NTC_ignore"))
    rows.append(row_buttons)
  # Добавляем все ряды в markup
  for row_buttons in rows:
      markup.row(*row_buttons)
  # Кнопка "Другое количество" в отдельном ряду
  markup.add(telebot.types.InlineKeyboardButton(text="Другое количество", callback_data=f"{user_id}_NTC_{command}_amount_other"))
  return markup

###################################################################################################
##                                       ОБРАБОТКА КОЛБЕКОВ                                      ##
###################################################################################################

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: telebot.types.CallbackQuery):
  # Берем id пользователя из чата для запоминания его выбора
  chat_id = call.message.chat.id
  user_id = call.from_user.id
  user_sender = get_user(user_id)
  if user_id not in user_selected:
    user_selected[user_id] = None
  if not call.data.startswith(str(user_id)):
    bot.answer_callback_query(call.id, "Эта кнопка не для вас!", show_alert=True)
    return
  # Игнорируем нажатия по пустым кнопкам
  if call.data == f"{user_id}_NTC_ignore":
    bot.answer_callback_query(call.id)
  # Команда /give, блок user 
  elif call.data.startswith(f"{user_id}_NTC_give_user"):
    bot.edit_message_reply_markup(
      chat_id=call.message.chat.id,
      message_id=call.message.message_id,
      reply_markup=None
      )
    print("GIVE: step 2")
    if user_id not in transactions_new:
      print("ERROR: Missing the beginning of a transaction")
      bot.send_message(chat_id, "Ошибка! Отсутствует начало транзакции. Начните транзакцию снова")
      return
    else:
      transaction = transactions_new[user_id]
    if call.data == f"{user_id}_NTC_give_user_other":
      msg = bot.send_message(chat_id, f"@{user_sender.username}, напишите в ответ на это сообщение Username пользователя, которому Вы хотите передать Ничего.")
      bot.register_next_step_handler(msg, give_step_taker)
      return
    else:
      transaction.user_taker = get_user(call.data.split("_", 4)[4][1:])
      transactions_new[user_id] = transaction
      bot.send_message(chat_id, f"Выберите количество ничего, которое Вы хотите отправить пользователю @{transaction.user_taker.username}:", reply_markup=keyboard_give_amount(user_id, 'give'))
      return
  # Команда /give, блок amount
  elif call.data.startswith(f"{user_id}_NTC_give_amount"):
    bot.edit_message_reply_markup(
      chat_id=call.message.chat.id,
      message_id=call.message.message_id,
      reply_markup=None
    )
    print("GIVE: step 3")
    if user_id not in transactions_new:
      print("ERROR: Missing the beginning of a transaction")
      bot.send_message(chat_id, "Ошибка! Отсутствует начало транзакции. Начните транзакцию снова")
      return
    else:
      transaction : Transaction = transactions_new[user_id]
    if call.data == f"{user_id}_NTC_give_amount_other":
      msg = bot.send_message(chat_id, "Напишите в ответ на это сообщение количество Ничего, которое хотите передать.")
      bot.register_next_step_handler(msg, give_step_amount)
      return
    else:
      transaction.amount = int(call.data.split("_", 4)[4])
      if check_amount(transaction.amount, chat_id) == False: return
      if transaction.check_transaction(chat_id) == False: return
      print("SUCCESS: Command is valid")
      transaction.transaction(chat_id)
      del transactions_new[user_id]
      return
  # Команда /balance_add, блок user 
  elif call.data.startswith(f"{user_id}_NTC_balanceadd_user"):
    if get_user(user_id).check_admin() == False: return 
    bot.edit_message_reply_markup(
      chat_id=call.message.chat.id,
      message_id=call.message.message_id,
      reply_markup=None
      )
    print("BALANCE_ADD: step 2")
    if user_id not in admin_transactions_new:
      print("ERROR: Missing the beginning of a transaction")
      bot.send_message(chat_id, "Ошибка! Отсутствует начало транзакции. Начните транзакцию снова")
      return
    else:
      transaction = admin_transactions_new[user_id]
    if call.data == f"{user_id}_NTC_balanceadd_user_other":
      msg = bot.send_message(chat_id, f"@{user_sender.username}, напишите в ответ на это сообщение Username пользователя, которому Вы хотите передать Ничего.")
      bot.register_next_step_handler(msg, balanceadd_step_taker, get_user(user_id))
      return
    else:
      transaction.user_taker = get_user(call.data.split("_", 4)[4][1:])
      admin_transactions_new[user_id] = transaction
      bot.send_message(chat_id, f"Выберите количество ничего, которое Вы хотите отправить пользователю @{transaction.user_taker.username}:", reply_markup=keyboard_give_amount(user_id, 'balanceadd'))
      return
  # Команда /balance_add, блок amount
  elif call.data.startswith(f"{user_id}_NTC_balanceadd_amount"):
    if get_user(user_id).check_admin() == False: return 
    bot.edit_message_reply_markup(
      chat_id=call.message.chat.id,
      message_id=call.message.message_id,
      reply_markup=None
    )
    print("BALANCE_ADD: step 3")
    if user_id not in admin_transactions_new:
      print("ERROR: Missing the beginning of a transaction")
      bot.send_message(chat_id, "Ошибка! Отсутствует начало транзакции. Начните транзакцию снова")
      return
    else:
      transaction : Transaction = admin_transactions_new[user_id]
    if call.data == f"{user_id}_NTC_balanceadd_amount_other":
      msg = bot.send_message(chat_id, "Напишите в ответ на это сообщение количество Ничего, которое хотите передать.")
      bot.register_next_step_handler(msg, balanceadd_step_amount, get_user(user_id))
      return
    else:
      transaction.amount = int(call.data.split("_")[4])
      if check_amount_admin(transaction.amount, chat_id) == False: return
      transaction.user_giver.balance += transaction.amount
      if transaction.check_transaction(chat_id) == False: 
        transaction.user_giver.balance -= transaction.amount
        return
      with lock:
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (transaction.amount, transaction.user_giver.id))
        database.commit()
      print("SUCCESS: Command is valid")
      transaction.transaction(chat_id)
      del admin_transactions_new[user_id]
      return

###################################################################################################
##                                             КОМАНДЫ                                           ##
###################################################################################################

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message:telebot.types.Message):
  print_message(message)
  # Добавьте пользователя в базу данных, если его еще нет
  if check_user(message.from_user.id) is False:
    user = User(message.from_user.id, message.from_user.username, random.randint(NOTHING_DEFAULT_MIN, NOTHING_DEFAULT_MAX))
    if user.check_admin() == True: secret_commands_doc = f'\n{message.from_user.first_name}, ты админ! Тебе доступны следующие секретные команды:\n1. /balance_add - добавить несколько Ничего на счет пользователя (в том числе и отрицательное количество).\n2. /balance_set - установить баланс пользователя.\n3. /balance_all - Список всех пользователей с их балансами.\n4. /stats_all - Статистика по всем пользователям.\n'
    else: secret_commands_doc = ''
    cursor.execute("INSERT INTO users (id, username, balance) VALUES (?, ?, ?)", (user.id, user.username, user.balance))
    database.commit()
    bot.reply_to(message, f"Привет, {message.from_user.first_name}!\nЯ бот для обмена ничем. Вот как мной пользоваться:\n1. /give - передать несколько Ничего пользователю.\n2. /balance - проверить свой текущий баланс.\n3. /history - посмотреть историю транзакций.\n4. /stats - посмотреть cвою статистику по транзакциям.\n{secret_commands_doc}\nТвой начальный баланс: {user.balance} Ничего.\nПомни, что Ничего - это довольно ценная валюта, так что передавай её с умом!\n\nУдачи!")
    print("SUCCESS: User is registered, balance and commands are sent")
  else:
    user = get_user(message.from_user.id)
    if user.check_admin() == True: secret_commands_doc = f'\n{message.from_user.first_name}, ты админ! Тебе доступны следующие секретные команды:\n1. /balance_add - добавить несколько Ничего на счет пользователя (в том числе и отрицательное количество).\n2. /balance_set - установить баланс пользователя.\n3. /balance_all - Список всех пользователей с их балансами.\n4. /stats_all - Статистика по всем пользователям.\n'
    else: secret_commands_doc = ''
    bot.reply_to(message, f"Привет, {message.from_user.first_name}!\nТы уже зарегистрирован на бирже Ничего!\n\nТвой баланс: {user.balance} Ничего\n\nКоманды:\n1. /give - передать несколько Ничего пользователю.\n2. /balance - проверить свой текущий баланс.\n3. /history - посмотреть историю транзакций.\n4. /stats - посмотреть cвою статистику по транзакциям.\n{secret_commands_doc}")
    print("SUCCESS: User is already registered, balance and commands are sent")
  print_user_db()
  return

####################################################################################################

# Обработчик команды /give
@bot.message_handler(commands=['give'])
def give(message:telebot.types.Message):
  chat_id = message.chat.id
  user_id = message.from_user.id
  print_message(message)
  print("GIVE: step 1")
  user_giver = get_user(message.from_user.id)
  if check_sender(user_giver, chat_id) == False: return
  transactions_new[user_id] = Transaction(user_giver)
  print("GIVE: Separate commands")
  user_selected[message.chat.id] = None
  user_list = set()
  if message.chat.type in ["group","supergroup","channel"]:
    for user in get_users_all(): 
      try:
        status = bot.get_chat_member(message.chat.id, user.id).status
        if status in ['member', 'administrator', 'creator']:
            print(f"User is in the chat: {status}")
            user_list.update(user.id)
        else:
            print(f"User is not in the chat: {status}")
      except telebot.apihelper.ApiTelegramException as e:
        print(f"ERROR: Can't get user information: {e}") 
  else:
    user_history = user_giver.get_transactions()
    for item in user_history: user_list.update(set([item.user_giver.id,item.user_taker.id])) 
    if len(user_list) == 0:
      print("NOTE: No transactions were found. Reply logic initiated.")
      msg = bot.reply_to(message, "Напишите в ответ на это сообщение Username пользователя, которому хотите передать Ничего.")
      bot.register_next_step_handler(msg, give_step_taker)
      return 
  user_list.remove(user_giver.id)
  user_list.remove(user_bot.id)
  bot.send_message(message.chat.id, "Выберите пользователя, которому Вы хотите отправить ничего:", reply_markup=keyboard_give_user(message.from_user.id, user_list, 'give'))
  return

def give_step_taker(message:telebot.types.Message):
  print_message(message)
  user_id = message.from_user.id
  chat_id = message.chat.id
  if user_id not in transactions_new:
    print("ERROR: Missing the beginning of a transaction")
    bot.send_message(chat_id, "Ошибка! Отсутствует начало транзакции. Начните транзакцию снова")
    return
  else:
      transaction : Transaction = transactions_new[user_id]
  if transaction.user_giver.id not in [message.from_user.id, user_bot.id]:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{transaction.user_giver.username}, а не от @{message.from_user.username}!")
    return
  print("GIVE: step 2")
  transaction.user_taker = get_user(message.text.replace("@", ""))
  print(transaction)
  if check_taker(transaction.user_taker, transaction.user_giver, chat_id) == False: return
  # msg = bot.reply_to(message, "Напишите в ответ на это сообщение количество Ничего, которое хотите передать.")
  # bot.register_next_step_handler(msg, give_step_amount, transaction)
  bot.send_message(message.chat.id, f"Выберите количество ничего, которое Вы хотите отправить пользователю {transaction.user_taker.username}", reply_markup=keyboard_give_amount(message.from_user.id, 'give'))

def give_step_amount(message:telebot.types.Message):
  print_message(message)
  user_id = message.from_user.id
  chat_id = message.chat.id
  if user_id not in transactions_new:
    print("ERROR: Missing the beginning of a transaction")
    bot.send_message(chat_id, "Ошибка! Отсутствует начало транзакции. Начните транзакцию снова")
    return
  else:
      transaction : Transaction = transactions_new[user_id]
  if transaction.user_giver.id not in [message.from_user.id, user_bot.id]:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{transaction.user_giver.username}, а не от @{message.from_user.username}!")
    return
  print("GIVE: step 3")
  transaction.amount = int(message.text)
  if check_amount(transaction.amount, chat_id) == False: return
  if transaction.check_transaction(chat_id) == False: return
  print("SUCCESS: Command is valid")
  transaction.transaction(chat_id)
  del transactions_new[user_id]

####################################################################################################

# Обработчик команды /balance
@bot.message_handler(commands=['balance'])
def balance(message:telebot.types.Message):
  chat_id = message.chat.id
  user = User()
  print_message(message)
  usernames = message.text.split(' ')
  if len(usernames) == 1:
    user = get_user(message.from_user.username)
    if check_sender(user, chat_id) == False: return
    bot.send_message(message.chat.id, f"{message.from_user.first_name}, твой баланс: {user.balance} Ничего.")
    print("SUCCESS: Balance is sent")
  else:
    if get_user(message.from_user.id).check_admin() == False: 
      bot.send_message(message.chat.id, "Вы можете узнать только свой баланс! Для этого введите /balance без последующих username пользователей.")
      return
    output = f"{message.from_user.first_name}, балансы запрашиваемых пользователей:\n"
    for i in range(1, len(usernames)):
      user = get_user(usernames[i].replace("@", ""))
      if user is None:
        bot.reply_to(message, f"{usernames[i]}: Пользователь не найден!")
        return
      else:
        output = f"{output}\nБаланс пользователя @{user.username}: {user.balance} Ничего.\n"
      bot.send_message(message.chat.id, output)
      print("SUCCESS: Balance is sent")
  print_user_db()
  return

####################################################################################################

# Обработчик команды /balance_all
@bot.message_handler(commands=['balance_all'])
def balance_all(message:telebot.types.Message):
  print_message(message)
  if get_user(message.from_user.id).check_admin() == False: return
  users = get_users_all()
  #Сортировка по балансу
  users.sort(key=lambda x: x.balance, reverse=True)
  output = f"{message.from_user.first_name}, вот баланс всех пользователей:\n"
  for i in range(len(users)):
    user:User = users[i]
    output = f"{output}\n{i+1}. @{user.username}: {user.balance} Ничего."
  bot.send_message(message.chat.id, output)
  print("SUCCESS: Balance is sent")
  print_user_db()
  return

####################################################################################################

# Обработчик команды /stats
@bot.message_handler(commands=['stats'])
def stats(message:telebot.types.Message):
  print_message(message)
  usernames = message.text.split(' ')
  if len(usernames) == 1:
    username = message.from_user.username
    user = get_user(username)
    if user is None:
      bot.reply_to(message, f"@{username}: Пользователь не найден!")
      print("ERROR: User is not found")
      return
    else:
      transactions = user.get_transactions()
      user_stats = [[0,0],[0,0]]
      transaction:Transaction
      for transaction in transactions:
        if transaction.user_giver.id == user.id:
          user_stats[0][0] += 1
          user_stats[0][1] += transaction.amount
        if transaction.user_taker.id == user.id:
          user_stats[1][0] += 1
          user_stats[1][1] += transaction.amount
      bot.send_message(message.chat.id, f"{message.from_user.first_name}, твоя статистика:\nБаланс: {user.balance} Ничего\n\nПередано: {user_stats[0][1]} Ничего\nПолучено: {user_stats[1][1]} Ничего\nВсего транзакций по передаче: {user_stats[0][0]}\nВсего транзакций по получению: {user_stats[1][0]}")
      print("SUCCESS: Stats are sent")
  else:
    if get_user(message.from_user.id).check_admin() == False: 
      bot.send_message(message.chat.id, "Вы можете посмотреть только свою статистику! Для этого введите /stats без последующих username пользователей.")
      return
    output = f"{message.from_user.first_name}, вот статистика по пользователям:\n"
    for i in range(1, len(usernames)):
      user = get_user(usernames[i].replace("@", ""))
      if user is None:
        bot.reply_to(message, f"{usernames[i]}: Пользователь не найден!")
        print("ERROR: User is not found")
        return
      else:
        transactions = user.get_transactions()
        user_stats = [[0,0],[0,0]]
        for transaction in transactions:
          if transaction.user_giver.id == user.id:
            user_stats[0][0] += 1
            user_stats[0][1] += transaction.amount
          if transaction.user_taker.id == user.id:
            user_stats[1][0] += 1
            user_stats[1][1] += transaction.amount
        output = f"{output}\n{i}. @{user.username}\nБаланс: {user.balance} Ничего\n\nПередано: {user_stats[0][1]} Ничего\nПолучено: {user_stats[1][1]} Ничего\nВсего транзакций по передаче: {user_stats[0][0]}\nВсего транзакций по получению: {user_stats[1][0]}"
    bot.send_message(message.chat.id, output)
    print("SUCCESS: Stats are sent")
  print_user_db()
  return

####################################################################################################

# Обработчик команды /stats_all
@bot.message_handler(commands=['stats_all'])
def stats_all(message:telebot.types.Message):
  print_message(message)
  if get_user(message.from_user.id).check_admin() == False: return
  users = get_users_all()
  if users is None:
    print('ERROR: Empty users database!')
    return
  users.sort(key=lambda x: x.balance, reverse=True)
  output = f"{message.from_user.first_name}, вот статистика всех пользователей:\n"
  for i in range(len(users)):
    user:User = users[i]
    transactions = user.get_transactions()
    transaction: Transaction
    user_stats = [[0,0],[0,0]]
    for transaction in transactions:
      if transaction.user_giver.id == user.id:
        user_stats[0][0] += 1
        user_stats[0][1] += transaction.amount
      if transaction.user_taker.id == user.id:
        user_stats[1][0] += 1
        user_stats[1][1] += transaction.amount
    output = f"{output}\n{i+1}. @{user.username}:\nБаланс: {user.balance} Ничего\nПередано: {user_stats[0][1]} Ничего\nПолучено: {user_stats[1][1]} Ничего\nВсего транзакций по передаче: {user_stats[0][1]}\nВсего транзакций по получению: {user_stats[1][0]}\n"
  bot.send_message(message.chat.id, output)
  print("SUCCESS: Balance is sent")
  print_user_db()
  return

####################################################################################################

# Обработчик команды /history
@bot.message_handler(commands=['history'])
def history(message:telebot.types.Message):
  print_trans_db()
  print_message(message)
  if len(message.text.split(' ',1)) == 1:
    username = message.from_user.username
  else:
    if get_user(message.from_user.id).check_admin() == False: 
      bot.send_message(message.chat.id, "Вы можете посмотреть только свою историю! Для этого введите /history без последующих username пользователей.")
      return
    username = message.text.split(' ',1)[1].replace("@", "")
  user = get_user(username)
  if user is None:
    bot.reply_to(message, f"@{username}: Пользователь не найден!")
    print("ERROR: User is not found")
    return
  else:
    output = ""
    transactions = user.get_transactions()
    output_length = min(HISTORY_LENGTH, len(transactions))
    if output_length == 0:
      output = f"{message.from_user.first_name}, история транзакций пользователя @{username} пуста!\n"
      print("NOTE: empty history")
    else:
      for j in range (0, output_length):
        k=len(transactions)-1-j
        transaction: Transaction = transactions[k]
        print(f"iteration {j}")
        if user.id == transaction.user_giver.id:
          output = f"{output}\n{j+1}. {transaction.date} - Передано {transaction.amount} Ничего для @{transaction.user_taker.username}"
        elif user.id == transaction.user_taker.id:
          output = f"{output}\n{j+1}. {transaction.date} - Получено {transaction.amount} Ничего от @{transaction.user_giver.username}"
        else:
          print("ERROR: missing user")
          print(f"{user.id}, {transaction.user_giver}, {transaction.user_taker}")
          output = "Ошибка с обработкой базы данных. Обратитесь к разработчику-дуралею."
          bot.send_message(message.chat.id, output)
          return
    if output_length < HISTORY_LENGTH:
      output = f"{message.from_user.first_name}, история последних {HISTORY_LENGTH} транзакций пользователя @{user.username}:\n{output}"
    else:
      output = f"{message.from_user.first_name}, история всех транзакций пользователя @{user.username}:\n{output}"
    bot.send_message(message.chat.id, output)
  print("SUCCESS: history is sent")
  return

####################################################################################################

# Обработчик команды /history_all
@bot.message_handler(commands=['history_all'])
def history_all(message:telebot.types.Message):
  print_trans_db()
  print_message(message)
  if get_user(message.from_user.id).check_admin() == False: return
  users = get_users_all()
  if users is None:
    print('ERROR: Empty users database!')
    return
  output = f"{message.from_user.first_name}, история последних {HISTORY_LENGTH} транзакций всех пользователей:\n"
  transactions = get_transactions_all()
  if len(transactions) == 0:
    output = f"{message.from_user.first_name}, история транзакций пуста!\n"
    print("NOTE: empty history")
  else:
    for j in range (0, min(HISTORY_LENGTH, len(transactions))):
      k=len(transactions)-1-j
      transaction: Transaction = transactions[k]
      print(f"iteration {j}")
      output = f"{output}\n{j+1}. {transaction.date} - @{transaction.user_giver.username} передал {transaction.amount} Ничего для @{transaction.user_taker.username}"
  bot.send_message(message.chat.id, output)
  print("SUCCESS: history is sent")
  return

####################################################################################################

# Обработчик команды /balance_add
@bot.message_handler(commands=['balance_add'])
def balance_add(message:telebot.types.Message):
  chat_id = message.chat.id
  user_id = message.from_user.id
  print_message(message)
  print("BALANCEADD: step 1")
  user_giver = user_bot
  admin_transactions_new[user_id] = Transaction(user_giver)
  print("BALANCEADD: Separate commands")
  user_selected[chat_id] = None
  user_list = set([user.id for user in get_users_all()])
  user_list.remove(user_giver.id)
  if len(user_list) == 0:
    print("NOTE: No transactions were found. Reply logic initiated.")
    msg = bot.reply_to(message, f"{message.from_user.first_name}, напиши Username пользователя, которому Биржа начислит Ничего")
    bot.register_next_step_handler(msg, balanceadd_step_taker, admin = get_user(user_id))
    return
  bot.send_message(chat_id, "Выберите пользователя, которому Вы хотите отправить ничего:", reply_markup=keyboard_give_user(message.from_user.id, user_list, 'balanceadd'))
  return

def balanceadd_step_taker(message:telebot.types.Message, admin: User):
  print_message(message)
  user_id = message.from_user.id
  chat_id = message.chat.id
  if user_id not in admin_transactions_new:
    print("ERROR: Missing the beginning of a transaction")
    bot.send_message(chat_id, "Ошибка! Отсутствует начало транзакции. Начните транзакцию снова")
    return
  else:
      transaction : Transaction = admin_transactions_new[user_id]
  if message.from_user.id != admin.id:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{admin.username}, а не от @{message.from_user.username}!")
    return
  print("GIVE: step 2")
  transaction.user_taker = get_user(message.text.replace("@", ""))
  print(transaction)
  if check_taker(transaction.user_taker, transaction.user_giver, chat_id) == False: return
  # msg = bot.reply_to(message, "Напишите в ответ на это сообщение количество Ничего, которое хотите передать.")
  # bot.register_next_step_handler(msg, balanceadd_step_amount, transaction)
  bot.send_message(message.chat.id, f"Выберите количество ничего, которое Вы хотите отправить пользователю {transaction.user_taker.username}", reply_markup=keyboard_give_amount(message.from_user.id, 'balanceadd'))

def balanceadd_step_amount(message:telebot.types.Message, admin:User):
  print_message(message)
  user_id = message.from_user.id
  chat_id = message.chat.id
  if user_id != admin.id:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{admin.username}, а не от @{message.from_user.username}!")
    return
  if user_id not in admin_transactions_new:
    print("ERROR: Missing the beginning of a transaction")
    bot.send_message(chat_id, "Ошибка! Отсутствует начало транзакции. Начните транзакцию снова")
    return
  else:
      transaction : Transaction = admin_transactions_new[user_id]
  print("BALANCE_ADD: step 3")
  transaction.amount = int(message.text)
  if check_amount_admin(transaction.amount, chat_id) == False: return
  transaction.user_giver.balance += transaction.amount
  if transaction.check_transaction(chat_id) == False: 
    transaction.user_giver.balance -= transaction.amount
    return
  with lock:
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (transaction.amount, transaction.user_giver.id))
    database.commit()
  print("SUCCESS: Command is valid")
  del admin_transactions_new[user_id]
  transaction.transaction(chat_id)

####################################################################################################

# Обработчик команды /balance_set
@bot.message_handler(commands=['balance_set'])
def balance_set(message:telebot.types.Message):
  print_message(message)
  admin: User = get_user(message.from_user.id)
  if get_user(admin.id).check_admin() == False: return
  print("BALANCE_SET: step 1")
  transaction = Transaction(user_giver = user_bot)
  #Команда с двумя аргументами
  #if len(message.text.split(' ')) == 3:
  #  print("Is3")
  #  tr_data.amount = message.text.split(' ', 2)[1]
  #  if check_amount(tr_data.amount, chat_id) == False: return
  #  username_taker = message.text.split(' ', 2)[2].replace("@", "")
  #  if check_taker(username_taker, tr_data.user_giver, chat_id) == False: return
  #  with lock:
  #    cursor.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username_taker,))
  #    tr_data.user_taker = cursor.fetchone()
  #  print("SUCCESS: Command is valid")
  #  #Отправка Ничего
  #  transaction(tr_data, chat_id)
  #  return
  #else:
  print("BALANCE_ADD: Separate commands")
  msg = bot.reply_to(message, f"{message.from_user.first_name}, напиши в ответ на это сообщение Username пользователя, которому Биржа установит количество Ничего")
  bot.register_next_step_handler(msg, balance_set_step_taker, transaction, admin)

def balance_set_step_taker(message:telebot.types.Message, transaction:Transaction, admin:User):
  chat_id = message.chat.id
  print_message(message)
  if message.from_user.id != admin.id:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{admin.username}, а не от @{message.from_user.username}!")
    return
  print("BALANCE_ADD: step 2")
  transaction.user_taker = get_user(message.text.replace("@", ""))
  print(transaction)
  if check_taker(transaction.user_taker, transaction.user_giver, chat_id) == False: return
  msg = bot.reply_to(message, "Напиши в ответ на это сообщение количество Ничего, которое Биржа установит пользователю")
  bot.register_next_step_handler(msg, balance_set_step_amount, transaction, admin)

def balance_set_step_amount(message:telebot.types.Message, transaction:Transaction, admin:User):
  print_message(message)
  chat_id = message.chat.id
  if message.from_user.id != admin.id:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{admin.username}, а не от @{message.from_user.username}!")
    return
  print("BALANCE_ADD: step 3")
  transaction.amount = int(message.text) - transaction.user_taker.balance
  if check_amount_admin(transaction.amount, chat_id) == False: return
  transaction.user_giver.balance += transaction.amount
  if transaction.check_transaction(chat_id) == False: 
    transaction.user_giver.balance -= transaction.amount
    return
  with lock:
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (transaction.amount, transaction.user_giver.id))
    database.commit()
  print("SUCCESS: Command is valid")
  transaction.transaction(chat_id)

###################################################################################################
##                                          ЗАПУСК БОТА                                          ##
###################################################################################################

#запускаем flask-сервер в отдельном потоке.
#keep_alive()

#запуск бота
bot.polling(non_stop=True, interval=0)