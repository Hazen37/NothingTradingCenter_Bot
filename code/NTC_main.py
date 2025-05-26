# Импорты
import os
from telebot.types import TransactionPartner
#from background import keep_alive #импорт функции для поддержки работоспособности
import pip
pip.main(['install', 'pytelegrambotapi'])
import telebot
import time
import sqlite3
import threading
import datetime
import random
lock = threading.Lock()

#Константы
BOT_TEST_TOKEN = '7708186142:AAG5FTQmYFS14FyRHdXXYF-BphHKk5op0_U' # Токен тестовой версии бота
BOT_RELEASE_TOKEN = '7662176920:AAGsNltswUDwT_d4Ha_IjA2neQYnpIhYx48' # Токен релизной версии бота
TRANSACTION_LIMIT = 10 # Максимальное количество Ничего в транзакции
HISTORY_LENGTH = 10 # Максимальная длина вывода статистики
NOTHING_DEFAULT_MIN = 5 # Минимальное количество получаемых Ничего по умолчанию
NOTHING_DEFAULT__MAX = 15 # Максимальное количество получаемых Ничего по умолчанию
NOTHING_LOW_LIMIT = 0 # Минимальное количество Ничего у пользователя
NOTHING_HIGH_LIMIT = None # Максимальное колтчество Ничего у пользователя
ADMIN_LIST = { # Список людей, которые могут использовать админские функции
  'eugenius_lesh',
  'grechka37'
}

####################################################################################################
#Выбор режима работы (тест/релиз)
if input("Hello! Is this a test or release?\n(Input 'R' if this is the release version)") == "R":
  BOT_TOKEN = BOT_RELEASE_TOKEN
  print("WARNING: RUNNING THE RELEASE MODE!")
else:
  BOT_TOKEN = BOT_TEST_TOKEN
  print("SUCCESS: running the TESTING mode")

# Создание бота
bot = telebot.TeleBot(BOT_TOKEN)
print(f'SUCCESS: Bot created!')
# Подключение к базе данных пользователей SQLite
SCRIPT_PATH = f'{os.path.dirname(os.path.abspath(__file__))}'
if not os.path.exists(f"{SCRIPT_PATH}/ntc_database.db"):
    open(f"{SCRIPT_PATH}/ntc_database.db", "w")
    print("SUCCESS: New database file is created!")
else:
    print("SUCCESS: Database file is found!")
database = sqlite3.connect(f"{SCRIPT_PATH}/ntc_database.db", check_same_thread=False)
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
  def transaction(self, message):
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
      bot.send_message(message.chat.id, f"@{self.user_giver.username} передал @{self.user_taker.username} {self.amount} Ничего!")
    else:
      bot.send_message(message.chat.id, f"Биржа начислила @{self.user_taker.username} {self.amount} Ничего!")
    try:
      member = bot.get_chat_member(chat_id=message.chat.id, user_id=self.user_taker.id)
      print("chatmember")
    except telebot.apihelper.ApiException as e:
      if self.user_giver.id != user_bot.id:
        bot.send_message(self.user_taker.id, f"Пользователь @{self.user_giver.username} передал Вам {self.amount} Ничего!\n\nВаш баланс: {self.user_taker.balance} Ничего.")
      else:
        bot.send_message(self.user_taker.id, f"Биржа начислила Вам {self.amount} Ничего!\n\nВаш баланс: {self.user_taker.balance} Ничего.")
      print("notachatmember")
      print_user_db()
  # Проверка транзакции
  def check_transaction(self, message):
    if NOTHING_HIGH_LIMIT is not None:
      if NOTHING_HIGH_LIMIT < self.user_taker.balance + self.amount:
        print("ERROR: Taker balance overflow")
        bot.reply_to(message, f"У получателя @{self.user_taker.username} станет слишком много ничего!\nПопробуйте отправить поменьше.")
        return(False)
      if NOTHING_HIGH_LIMIT < self.user_giver.balance - self.amount:
        print("ERROR: Giver balance overflow")
        bot.reply_to(message, f"У отправителя @{self.user_giver.username} станет слишком много ничего!\nПопробуйте отправить побольше.")
        return(False)
    if NOTHING_LOW_LIMIT is not None:
      if NOTHING_LOW_LIMIT > self.user_giver.balance - self.amount:
        print("ERROR: Giver balance underflow")
        bot.reply_to(message, f"{message.from_user.first_name}, у тебя нет столько ничего! Твой баланс {self.user_giver.balance} Ничего.\nПопроси у кого-нибудь еще!")
        return(False)
      if NOTHING_LOW_LIMIT > self.user_taker.balance + self.amount:
        print("ERROR: Taker balance underflow")
        bot.reply_to(message, f"{message.from_user.first_name}, у пользователя @{self.user_taker.username} станет слишком мало ничего!\nЕго баланс сейчас: {self.user_taker.balance} Ничего.")
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

def print_message(message):
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
def check_amount(amount, message):
  try:
    amount = int(amount)
  except ValueError:
    print("ERROR: Invalid amount")
    bot.reply_to(message, "Неверное количество Ничего!")
    return(False)
  #Проверка на нулевую передачу Ничего
  if amount == 0  :
    print("ERROR: Zero transaction")
    bot.reply_to(message, "Ха-ха, у нас тут Клоун. Вы не можете передать 0 Ничего!")
    return(False)
  #Проверка на отрицательную передачу Ничего
  if amount < 0  :
    print("ERROR: Negative transaction")
    bot.reply_to(message, "Ого, да Вы умны! Но к сожалению, Вы не можете передать отрицательное количество Ничего!")
    return(False)
  #Проверка на большое количество Ничего
  if amount > TRANSACTION_LIMIT:
    print("ERROR: Large transaction")
    bot.reply_to(message, f"Вы не можете передать больше {TRANSACTION_LIMIT} Ничего! Это Вам не деньги, чтобы их так тратить!")
    return(False)
  return(True)

def check_amount_admin(amount, message):
  try:
    amount = int(amount)
  except ValueError:
    print("ERROR: Invalid amount")
    bot.reply_to(message, "Неверное количество Ничего!")
    return(False)
  return(True)

#Проверка получающего
def check_taker(user_taker:User,user_giver:User, message):
  if user_taker is None:
    print("ERROR: Taker is not found")
    bot.reply_to(message, f"{message.text}: Пользователь не найден!")
    return(False)
    #Проверка на отправление себе
  if user_giver.id == user_taker.id:
      print("ERROR: Giver is taker")
      bot.reply_to(message, "Ха-ха, очень смешно. Вы не можете отправить самому себе Ничего!")
      return(False)
  if user_taker.id == user_bot.id:
      print("ERROR: Taker is bot")
      bot.reply_to(message, "Увы, Вы не можете передать Ничего боту! Почему Вы вообще попробовали это сделать?")
      return(False)
  return(True)

#Проверка отправляющего сообщение
def check_sender(user_giver:User, message):
  if user_giver is None:
    print("ERROR: Giver is not found")
    bot.reply_to(message, "Вы не зарегистрированы на бирже Ничего!\nЗарегистрируйтесь, чтобы начать обмениваться Ничем.")
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

####################################################################################################
####################################################################################################
# Обработчик команды /start

@bot.message_handler(commands=['start'])
def start(message):
  print_message(message)
  # Добавьте пользователя в базу данных, если его еще нет
  if check_user(message.from_user.id) is False:
    user = User(message.from_user.id, message.from_user.username, random.randint(NOTHING_DEFAULT_MIN, NOTHING_DEFAULT__MAX))
    cursor.execute("INSERT INTO users (id, username, balance) VALUES (?, ?, ?)", (user.id, user.username, user.balance))
    database.commit()
    bot.reply_to(message, f"Привет, {message.from_user.first_name}!\nЯ бот для обмена ничем. Вот как мной пользоваться:\n1. /give- передать несколько Ничего пользователю\n2. /balance - проверить свой текущий баланс\n3. /history - посмотреть историю транзакций\n4./stats - посмотреть cвою статистику по транзакциям\n\nТвой начальный баланс: {user.balance} Ничего.\nПомни, что Ничего - это довольно ценная валюта, так что передавай её с умом!\n\nУдачи!")
    print("SUCCESS: User is registered")
  else:
    user = get_user(message.from_user.id)
    bot.reply_to(message, f"Привет, {message.from_user.first_name}!\nТы уже зарегистрирован на бирже Ничего!\n\nТвой баланс: {user.balance} Ничего")
    print("SUCCESS: User is already registered, balance is sent")
  print_user_db()
  return

####################################################################################################
# Обработчик команды /give

@bot.message_handler(commands=['give'])
def give(message):
  print_message(message)
  print("GIVE: step 1")
  transaction = Transaction(user_giver = get_user(message.from_user.id))
  if check_sender(transaction.user_giver, message) == False: return
  #Команда с двумя аргументами
  #if len(message.text.split(' ')) == 3:
  #  print("Is3")
  #  tr_data.amount = message.text.split(' ', 2)[1]
  #  if check_amount(tr_data.amount, message) == False: return
  #  username_taker = message.text.split(' ', 2)[2].replace("@", "")
  #  if check_taker(username_taker, tr_data.user_giver, message) == False: return
  #  with lock:
  #    cursor.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username_taker,))
  #    tr_data.user_taker = cursor.fetchone()
  #  print("SUCCESS: Command is valid")
  #  #Отправка Ничего
  #  transaction(tr_data, message)
  #  return
  #else:
  print("GIVE: Separate commands")
  msg = bot.reply_to(message, "Напишите Username пользователя, которому хотите передать Ничего")
  bot.register_next_step_handler(msg, give_step_taker, transaction)

def give_step_taker(message, transaction:Transaction):
  print_message(message)
  if message.from_user.id != transaction.user_giver.id:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{transaction.user_giver.username}, а не от @{message.from_user.username}!")
    return
  print("GIVE: step 2")
  transaction.user_taker = get_user(message.text.replace("@", ""))
  print(transaction)
  if check_taker(transaction.user_taker, transaction.user_giver, message) == False: return
  msg = bot.reply_to(message, "Напишите количество Ничего, которое хотите передать")
  bot.register_next_step_handler(msg, give_step_amount, transaction)

def give_step_amount(message, transaction:Transaction):
  print_message(message)
  if message.from_user.id != transaction.user_giver.id:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{transaction.user_giver.username}, а не от @{message.from_user.username}!")
    return
  print("GIVE: step 3")
  transaction.amount = int(message.text)
  if check_amount(transaction.amount, message) == False: return
  if transaction.check_transaction(message) == False: return
  print("SUCCESS: Command is valid")
  transaction.transaction(message)

####################################################################################################
# Обработчик команды /balance

@bot.message_handler(commands=['balance'])
def balance(message):
  user = User()
  print_message(message)
  usernames = message.text.split(' ')
  if len(usernames) == 1:
    user = get_user(message.from_user.username)
    if check_sender(user, message) == False: return
    bot.send_message(message.chat.id, f"{message.from_user.first_name}, твой баланс: {user.balance} Ничего")
    print("SUCCESS: Balance is sent")
  else:
    output = f"{message.from_user.first_name}, балансы запрашиваемых пользователей:\n"
    for i in range(1, len(usernames)):
      user = get_user(usernames[i].replace("@", ""))
      if user is None:
        bot.reply_to(message, f"{usernames[i]}: Пользователь не найден!")
        return
      else:
        output = f"{output}\nБаланс пользователя @{user.username}: {user.balance} Ничего\n"
      bot.send_message(message.chat.id, output)
      print("SUCCESS: Balance is sent")
  print_user_db()
  return

####################################################################################################
# Обработчик команды /balance_all

@bot.message_handler(commands=['balance_all'])
def balance_all(message):
  print_message(message)
  if get_user(message.from_user.id).check_admin() == False: return
  users = get_users_all()
  #Сортировка по балансу
  users.sort(key=lambda x: x.balance, reverse=True)
  output = f"{message.from_user.first_name}, вот баланс всех пользователей:\n"
  for i in range(len(users)):
    user:User = users[i]
    output = f"{output}\n{i+1}. @{user.username}: {user.balance} Ничего"
  bot.send_message(message.chat.id, output)
  print("SUCCESS: Balance is sent")
  print_user_db()
  return

####################################################################################################
# Обработчик команды /stats

@bot.message_handler(commands=['stats'])
def stats(message):
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
def stats_all(message):
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
def history(message):
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
    output = f"{message.from_user.first_name}, история транзакций пользователя @{user.username}:\n"
    transactions = user.get_transactions()
    if len(transactions) == 0:
      output = f"{message.from_user.first_name}, история транзакций пользователя @{username} пуста!\n"
      print("NOTE: empty history")
    else:
      for j in range (0, min(HISTORY_LENGTH, len(transactions))):
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
    bot.send_message(message.chat.id, output)
  print("SUCCESS: history is sent")
  return

####################################################################################################
# Обработчик команды /history_all

@bot.message_handler(commands=['history_all'])
def history_all(message):
  print_trans_db()
  print_message(message)
  if get_user(message.from_user.id).check_admin() == False: return
  users = get_users_all()
  if users is None:
    print('ERROR: Empty users database!')
    return
  output = f"{message.from_user.first_name}, последняя история транзакций всех пользователей:\n"
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
def balance_add(message):
  print_message(message)
  admin: User = get_user(message.from_user.id)
  if get_user(admin.id).check_admin() == False: return
  print("BALANCE_ADD: step 1")
  transaction = Transaction(user_giver = user_bot)
  #Команда с двумя аргументами
  #if len(message.text.split(' ')) == 3:
  #  print("Is3")
  #  tr_data.amount = message.text.split(' ', 2)[1]
  #  if check_amount(tr_data.amount, message) == False: return
  #  username_taker = message.text.split(' ', 2)[2].replace("@", "")
  #  if check_taker(username_taker, tr_data.user_giver, message) == False: return
  #  with lock:
  #    cursor.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username_taker,))
  #    tr_data.user_taker = cursor.fetchone()
  #  print("SUCCESS: Command is valid")
  #  #Отправка Ничего
  #  transaction(tr_data, message)
  #  return
  #else:
  print("BALANCE_ADD: Separate commands")
  msg = bot.reply_to(message, f"{message.from_user.first_name}, напиши Username пользователя, которому Биржа начислит Ничего")
  bot.register_next_step_handler(msg, balance_add_step_taker, transaction, admin)

def balance_add_step_taker(message, transaction:Transaction, admin:User):
  print_message(message)
  if message.from_user.id != admin.id:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{admin.username}, а не от @{message.from_user.username}!")
    return
  print("BALANCE_ADD: step 2")
  transaction.user_taker = get_user(message.text.replace("@", ""))
  print(transaction)
  if check_taker(transaction.user_taker, transaction.user_giver, message) == False: return
  msg = bot.reply_to(message, "Напишите количество Ничего, которое Биржа начислит пользователю")
  bot.register_next_step_handler(msg, balance_add_step_amount, transaction, admin)

def balance_add_step_amount(message, transaction:Transaction, admin:User):
  print_message(message)
  if message.from_user.id != admin.id:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{admin.username}, а не от @{message.from_user.username}!")
    return
  print("BALANCE_ADD: step 3")
  transaction.amount = int(message.text)
  if check_amount_admin(transaction.amount, message) == False: return
  transaction.user_giver.balance += transaction.amount
  if transaction.check_transaction(message) == False: 
    transaction.user_giver.balance -= transaction.amount
    return
  with lock:
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (transaction.amount, transaction.user_giver.id))
    database.commit()
  print("SUCCESS: Command is valid")
  transaction.transaction(message)

####################################################################################################
# Обработчик команды /balance_set

@bot.message_handler(commands=['balance_set'])
def balance_set(message):
  print_message(message)
  admin: User = get_user(message.from_user.id)
  if get_user(admin.id).check_admin() == False: return
  print("BALANCE_SET: step 1")
  transaction = Transaction(user_giver = user_bot)
  #Команда с двумя аргументами
  #if len(message.text.split(' ')) == 3:
  #  print("Is3")
  #  tr_data.amount = message.text.split(' ', 2)[1]
  #  if check_amount(tr_data.amount, message) == False: return
  #  username_taker = message.text.split(' ', 2)[2].replace("@", "")
  #  if check_taker(username_taker, tr_data.user_giver, message) == False: return
  #  with lock:
  #    cursor.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username_taker,))
  #    tr_data.user_taker = cursor.fetchone()
  #  print("SUCCESS: Command is valid")
  #  #Отправка Ничего
  #  transaction(tr_data, message)
  #  return
  #else:
  print("BALANCE_ADD: Separate commands")
  msg = bot.reply_to(message, f"{message.from_user.first_name}, напиши Username пользователя, которому Биржа установит количество Ничего")
  bot.register_next_step_handler(msg, balance_set_step_taker, transaction, admin)

def balance_set_step_taker(message, transaction:Transaction, admin:User):
  print_message(message)
  if message.from_user.id != admin.id:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{admin.username}, а не от @{message.from_user.username}!")
    return
  print("BALANCE_ADD: step 2")
  transaction.user_taker = get_user(message.text.replace("@", ""))
  print(transaction)
  if check_taker(transaction.user_taker, transaction.user_giver, message) == False: return
  msg = bot.reply_to(message, "Напишите количество Ничего, которое Биржа начислит пользователю")
  bot.register_next_step_handler(msg, balance_set_step_amount, transaction, admin)

def balance_set_step_amount(message, transaction:Transaction, admin:User):
  print_message(message)
  if message.from_user.id != admin.id:
    print('ERROR: Sequence broken by different user!')
    bot.reply_to(message, f"Я ожидал сообщение от @{admin.username}, а не от @{message.from_user.username}!")
    return
  print("BALANCE_ADD: step 3")
  transaction.amount = int(message.text) - transaction.user_taker.balance
  if check_amount_admin(transaction.amount, message) == False: return
  transaction.user_giver.balance += transaction.amount
  if transaction.check_transaction(message) == False: 
    transaction.user_giver.balance -= transaction.amount
    return
  with lock:
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (transaction.amount, transaction.user_giver.id))
    database.commit()
  print("SUCCESS: Command is valid")
  transaction.transaction(message)

####################################################################################################
#запуск бота

#запускаем flask-сервер в отдельном потоке.
#keep_alive()

#запуск бота
bot.polling(non_stop=True, interval=0)