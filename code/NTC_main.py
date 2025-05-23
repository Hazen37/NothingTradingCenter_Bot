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
lock = threading.Lock()

#Константы
TOKEN = '7550619842:AAF7b_yAdVcDBtAeC2luFS367iYVwxeveLA' # Токен бота
TRANSACTION_LIMIT = 20 # Максимальное количество ничего в транзакции
HISTORY_LENGTH = 10 # Максимальная длина вывода статистики

####################################################################################################
# Создайте бот
bot = telebot.TeleBot(TOKEN)
# Подключение к базе данных пользователей SQLite
users_db = sqlite3.connect('databases/ntc_users.db', check_same_thread=False)
cursor_user = users_db.cursor()
# Создание БД пользователей, если она не существует
with lock:
  cursor_user.execute('''CREATE TABLE IF NOT EXISTS 
  users (
  id INTEGER PRIMARY KEY,
  username TEXT,
  nothing_gives INTEGER DEFAULT 0,
  nothing_takes INTEGER DEFAULT 0,
  transactions_gives INTEGER DEFAULT 0,
  transactions_takes INTEGER DEFAULT 0
  )''')
users_db.commit()
# Подключение к базе данных транзакций SQLite
transactions_db = sqlite3.connect('databases/ntc_transactions.db', check_same_thread=False)
cursor_tran = transactions_db.cursor()
# Создание БД транзакций, если она не существует
with lock:
  cursor_tran.execute('''CREATE TABLE IF NOT EXISTS 
  transactions (
  date TEXT PRIMARY KEY,
  user_id_giver INTEGER,
  user_id_taker INTEGER,
  nothing_number INTEGER
  )''')
users_db.commit()
####################################################################################################
#Класс транзакций
class Transaction:
  number = 0,
  user_taker = "",
  user_giver = "",
#Функция транзакции
def transaction(tr_data: Transaction, message):
  with lock:
    cursor_user.execute("UPDATE users SET nothing_gives = nothing_gives + ? WHERE id = ?", (tr_data.number, tr_data.user_giver[0]))
    cursor_user.execute("UPDATE users SET transactions_gives = transactions_gives + 1 WHERE id = ?", (tr_data.user_giver[0],))
    cursor_user.execute("UPDATE users SET nothing_takes = nothing_takes + ? WHERE id = ?", (tr_data.number, tr_data.user_taker[0]))
    cursor_user.execute("UPDATE users SET transactions_takes = transactions_takes + 1 WHERE id = ?", (tr_data.user_taker[0],))
    users_db.commit()
  datenow = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=3))).strftime("%d.%m.%Y %H:%M:%S")
  with lock:
    cursor_tran.execute("INSERT INTO transactions (date, user_id_giver, user_id_taker, nothing_number) VALUES (?, ?, ?, ?)", (datenow, tr_data.user_giver[0], tr_data.user_taker[0], tr_data.number))
    transactions_db.commit()
  bot.send_message(message.chat.id, f"@{tr_data.user_giver[1]} передал @{tr_data.user_taker[1]} {tr_data.number} Ничего!")
  print("SUCCESS: Nothing is given")
  try:
    member = bot.get_chat_member(chat_id=message.chat.id, user_id=tr_data.user_taker[0])
    print("chatmember")
  except telebot.apihelper.ApiException as e:
    bot.send_message(tr_data.user_taker[0], f"Пользователь @{tr_data.user_giver[1]} передал Вам {tr_data.number} Ничего!")
    print("notachatmember")
    print_user_db()

#Функция для вывода базы данных пользователей
def print_user_db():
  with lock:
    cursor_user.execute("SELECT * FROM users") # Выполнение запроса
    rows = cursor_user.fetchall() # Получение данных
  print("Printing database:\n id | username | n_given | n_taken | t_given | t_taken")
  for row in rows: # Вывод данных
    print(row)
  print("\n")

#Функция для вывода базы данных транзакций
def print_trans_db():
  with lock:
    cursor_tran.execute("SELECT * FROM transactions") # Выполнение запроса
    rows = cursor_tran.fetchall() # Получение данных
  print("Printing database:\n date | user_id_giver | user_id_taker | nothing_number")
  for row in rows: # Вывод данных
    print(row)
  print("\n")

def print_message(message):
   print(f'\n{message.from_user.username} says: {message.text}')
   
#####################################################################################################
#Блок Функций проверок
#Проверка на количество Ничего
def check_number(number, message):
    try:
        number = int(number)
    except ValueError:
        print("ERROR: Invalid number")
        bot.reply_to(message, "Неверное количество Ничего!")
        return(False)
    #Проверка на нулевую передачу Ничего
    if number == 0  :
        print("ERROR: Zero transaction")
        bot.reply_to(message, "Ха-ха, у нас тут Клоун. Вы не можете передать 0 Ничего!")
        return(False)
    #Проверка на отрицательную передачу Ничего
    if number < 0  :
        print("ERROR: Negative transaction")
        bot.reply_to(message, "Ого, да Вы умны! Но к сожалению, Вы не можете передать отрицательное количество Ничего!")
        return(False)
    #Проверка на большое количество Ничего
    if number > TRANSACTION_LIMIT:
        print("ERROR: Large transaction")
        bot.reply_to(message, f"Вы не можете передать больше {TRANSACTION_LIMIT} Ничего! Это Вам не деньги, чтобы их так тратить!")
        return(False)
    return(True)

#Проверка получающего
def check_taker(username_taker,user_giver, message):
    cursor_user.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username_taker,))
    user_taker = cursor_user.fetchone()
    if user_taker is None:
        print("ERROR: Taker is not found")
        bot.reply_to(message, f"{username_taker}: Пользователь не найден!")
        return(False)
    #Проверка на отправление себе
    if user_giver[0] == user_taker[0]:
        print("ERROR: Giver is taker")
        bot.reply_to(message, "Ха-ха, очень смешно. Вы не можете отправить самому себе Ничего!")
        return(False)
    return(True)

#Проверка отправляющего
def check_sender(user_giver, message):
    if user_giver is None:
        print("ERROR: Giver is not found")
        bot.reply_to(message, "Вы не зарегистрированы на бирже Ничего!")
        return(False)
    return(True)

####################################################################################################
# Обработчик команды /start

@bot.message_handler(commands=['start'])
def start(message):
  print_message(message)
  user_id = message.from_user.id
  username = message.from_user.username
  # Добавьте пользователя в базу данных, если его еще нет
  with lock:
    cursor_user.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor_user.fetchone()
  if user is None:
    cursor_user.execute("INSERT INTO users (id, username) VALUES (?, ?)", (user_id, username))
    users_db.commit()
    bot.reply_to(message, f"Привет, {message.from_user.first_name}!\nЯ бот для обмена ничем. Вот как мной пользоваться:\n1. /give- передать несколько Ничего пользователю\n2. /balance - проверить свой текущий баланс\n3. /history - посмотреть историю транзакций\n4./stats - посмотреть cвою статистику по транзакциям\n5. /my_stats - посмотреть свою статистику.\n\nТвой начальный баланс: {user[3]-user[2]} Ничего. Баланс может уйти в минус, ничего страшного.\nПомни, что Ничего - это довольно ценная валюта, так что передавай её с умом!\n\nУдачи!")
    print("SUCCESS: User is registered")
  else:
    bot.reply_to(message, f"Привет, {message.from_user.first_name}!\nТы уже зарегистрирован на бирже Ничего!\n\nТвой баланс: {user[3]-user[2]} Ничего")
    print("SUCCESS: User is already registered, balance is sent")
  print_user_db()
  return

####################################################################################################
# Обработчик команды /give

@bot.message_handler(commands=['give'])
def give(message):
  print_message(message)
  print("GIVE: step 1")
  tr_data = Transaction()
  with lock:
    cursor_user.execute("SELECT * FROM users WHERE id = ? COLLATE NOCASE", (message.from_user.id,))
    tr_data.user_giver = cursor_user.fetchone()
  tr_data.user_taker = tr_data.user_giver
  #Считывание команды
  #if check_sender(tr_data.user_giver, message) == False: return
  #if len(message.text.split(' ')) > 3:
  #  print("MoreThan3")
  #  print("ERROR: Invalid command")
  #  bot.reply_to(message, "Вы ошиблись в команде! Используйте /give <Кол-во Ничего> <Username пользователя>")
  #  return
  #Команда с двумя аргументами
  #if len(message.text.split(' ')) == 3:
  #  print("Is3")
  #  tr_data.number = message.text.split(' ', 2)[1]
  #  if check_number(tr_data.number, message) == False: return
  #  username_taker = message.text.split(' ', 2)[2].replace("@", "")
  #  if check_taker(username_taker, tr_data.user_giver, message) == False: return
  #  with lock:
  #    cursor_user.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username_taker,))
  #    tr_data.user_taker = cursor_user.fetchone()
  #  print("SUCCESS: Command is valid")
  #  #Отправка Ничего
  #  transaction(tr_data, message)
  #Команда с одним аргументом или без них
  #if len(message.text.split(' ')) < 3:
  print("GIVE: Separate commands")
  msg = bot.reply_to(message, "Напишите Username пользователя, которому хотите передать Ничего")
  bot.register_next_step_handler(msg, give_step_taker, tr_data)

def give_step_taker(message, tr_data:Transaction):
  print_message(message)
  print("GIVE: step 2")
  print(tr_data)
  username_taker = message.text.replace("@", "")
  with lock:
    cursor_user.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username_taker,))
    tr_data.user_taker = cursor_user.fetchone()
  print(tr_data.user_taker)
  if check_taker(username_taker, tr_data.user_giver, message) == False: return
  msg = bot.reply_to(message, "Напишите количество Ничего, которое хотите передать")
  bot.register_next_step_handler(msg, give_step_number, tr_data)

def give_step_number(message, tr_data:Transaction):
  print_message(message)
  print("GIVE: step 3")
  tr_data.number = int(message.text)
  if check_number(tr_data.number, message) == False: return
  #print("SUCCESS: Command is valid\n")
  transaction(tr_data, message)

####################################################################################################
# Обработчик команды /balance

@bot.message_handler(commands=['balance'])
def balance(message):
  print_message(message)
  usernames = message.text.split(' ')
  if len(usernames) == 1:
    username = message.from_user.username
    with lock:
      cursor_user.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
      user = cursor_user.fetchone()
    if user is None:
      bot.reply_to(message, f"@{username}: Пользователь не найден!")
      print("ERROR: User is not found")
      return
    else:
      bot.send_message(message.chat.id, f"{message.from_user.first_name}, твой баланс: {user[3]-user[2]} Ничего")
      print("SUCCESS: Balance is sent")
  else:
    output = ""
    for i in range(1, len(usernames)):
      usernames[i] = usernames[i].replace("@", "")
      with lock:
        cursor_user.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (usernames[i],))
        user = cursor_user.fetchone()
      if user is None:
        bot.reply_to(message, f"{usernames[i]}: Пользователь не найден!")
        print("ERROR: User is not found")
        return
      else:
        output = f"{output}Баланс пользователя @{user[1]}: {user[3]-user[2]} Ничего\n";
      bot.send_message(message.chat.id, output)
      print("SUCCESS: Balance is sent")
  print_user_db()

####################################################################################################
# Обработчик команды /balance_all

@bot.message_handler(commands=['balance_all'])
def balance_all(message):
  print_message(message)
  with lock:
    cursor_user.execute("SELECT * FROM users") # Выполнение запроса
    users = cursor_user.fetchall() # Получение данных
  #Сортировка по балансу
  users.sort(key=lambda x: x[3]-x[2], reverse=True)
  output = f"{message.from_user.first_name}, вот баланс всех пользователей:\n"
  for i in range(len(users)):
    output = f"{output}\n{i+1}. @{users[i][1]}: {users[i][3]-users[i][2]} Ничего";
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
    with lock:
      cursor_user.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
      user = cursor_user.fetchone()
    if user is None:
      bot.reply_to(message, f"@{username}: Пользователь не найден!")
      print("ERROR: User is not found")
      return
    else:
      bot.send_message(message.chat.id, f"{message.from_user.first_name}, твоя статистика:\nБаланс: {user[3]-user[2]} Ничего\n\nПередано: {user[2]} Ничего\nПолучено: {user[3]} Ничего\nВсего транзакций по передаче: {user[4]}\nВсего транзакций по получению: {user[5]}")
      print("SUCCESS: Stats are sent")
  else:
    output = f"{message.from_user.first_name}, вот статистика по пользователям:\n"
    for i in range(1, len(usernames)):
      usernames[i] = usernames[i].replace("@", "")
      with lock:
        cursor_user.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (usernames[i],))
        user = cursor_user.fetchone()
      if user is None:
        bot.reply_to(message, f"{usernames[i]}: Пользователь не найден!")
        print("ERROR: User is not found")
        return
      else:
        output = f"{output}\n{i}. @{user[1]}\nБаланс: {user[3]-user[2]} Ничего\nПередано: {user[2]} Ничего\nПолучено: {user[3]} Ничего\nВсего транзакций по передаче: {user[4]}\nВсего транзакций по получению: {user[5]}\n";
    bot.send_message(message.chat.id, output)
    print("SUCCESS: Stats are sent")
  print_user_db()
  return

####################################################################################################
# Обработчик команды /stats_all

@bot.message_handler(commands=['stats_all'])
def stats_all(message):
  print_message(message)
  with lock:
    cursor_user.execute("SELECT * FROM users") # Выполнение запроса
    users = cursor_user.fetchall() # Получение данных
  #Сортировка по балансу
  users.sort(key=lambda x: x[3]-x[2], reverse=True)
  output = f"{message.from_user.first_name}, вот статистика всех пользователей:\n"
  for i in range(len(users)):
    output = f"{output}\n{i+1}. @{users[i][1]}:\nБаланс: {users[i][3]-users[i][2]} Ничего\nПередано: {users[i][2]} Ничего\nПолучено: {users[i][3]} Ничего\nВсего транзакций по передаче: {users[i][4]}\nВсего транзакций по получению: {users[i][5]}\n"
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
  usernames = message.text.split(' ',1)
  if len(usernames) == 1:
    username = message.from_user.username
    output = f"{message.from_user.first_name}, твоя история транзакций:\n"
  if len(usernames) > 1:
    username = usernames[1].replace("@", "")
    output = f"{message.from_user.first_name}, история транзакций пользователя @{username}:\n"
  with lock:
    cursor_user.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
    user = cursor_user.fetchone()
  if user is None:
    bot.reply_to(message, f"@{username}: Пользователь не найден!")
    print("ERROR: User is not found")
    return
  else:
    with lock:
        cursor_tran.execute("SELECT * FROM transactions WHERE user_id_giver = ? OR user_id_taker = ?", (user[0], user[0],))
        history_list = cursor_tran.fetchall()
    if len(history_list) == 0:
      output = f"{message.from_user.first_name}, твоя история транзакций пуста!\n"
      print("NOTE: empty history")
    else:
      for j in range (0, min(HISTORY_LENGTH, len(history_list))):
        k=len(history_list)-1-j
        print(f"iteration {j}")
        if user[0] == history_list[k][1]:
          with lock:
            cursor_user.execute("SELECT * FROM users WHERE id = ? COLLATE NOCASE", (history_list[k][2],))
            user_transactor = cursor_user.fetchone()
          output = f"{output}\n{j+1}. {history_list[k][0]} - Передано {history_list[k][3]} Ничего для @{user_transactor[1]}"
        elif user[0] == history_list[k][2]:
          with lock:
            cursor_user.execute("SELECT * FROM users WHERE id = ? COLLATE NOCASE", (history_list[k][1],))
            user_transactor = cursor_user.fetchone()
          output = f"{output}\n{j+1}. {history_list[k][0]} - Получено {history_list[k][3]} Ничего от @{user_transactor[1]}"
        else:
          print("ERROR: missing user")
          print(f"{user[0]}, {history_list[k][1]}, {history_list[k][2]}")
          output = "Ошибка с обработкой базы данных. Обратитесь к разработчику-дуралею."
          bot.send_message(message.chat.id, output)
          return
    bot.send_message(message.chat.id, output)
    print("SUCCESS: history is sent")
  return

####################################################################################################
#запуск бота

#запускаем flask-сервер в отдельном потоке.
#keep_alive()

#запуск бота
bot.polling(non_stop=True, interval=0)