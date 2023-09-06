from flask import Flask, request
import requests
import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta

bot = telebot.TeleBot('6604097152:AAHB0Kr1P92O6b5zjlJGlP1cOuO9Kswz2Ws')

users = [] # Динамический массив хранящий id текущих пользователей
orders = set() #
admins = [574752230, 350591707] # Статический массив с id администраторов

conn = sqlite3.connect("users_bot.sql")
cur = conn.cursor()
# cur.execute('DROP TABLE IF EXISTS users')
# cur.execute('CREATE TABLE users (id int primary key, username varchar(50), first_name varchar(50),start_date datetime, duration varchar(10), end_of_date datetime)')
cur.execute('CREATE TABLE IF NOT EXISTS users (id int primary key, username varchar(50), first_name varchar(50),start_date datetime, duration varchar(10), end_of_date datetime)')
conn.commit()
cur.execute('CREATE TABLE IF NOT EXISTS orderss (user_id int, external_id int, order_id varchar(20), duration varchar(10), start_date datetime)')
conn.commit()

cur.execute('SELECT * FROM users') # Заполнение массива users пользователями из базы данных
usersSQL = cur.fetchall()
if len(usersSQL) > 0:
    for el in usersSQL:
        users.append(int(el[0]))
cur.execute('SELECT * FROM orders')
ordersSQL = cur.fetchall()
if len (ordersSQL) > 0:
    for el in ordersSQL:
        orders.add(int(el[0]))
cur.close()
conn.close()

external_id = 1006
def postOrder(amount, duration, user_id):
    global external_id
    if user_id in orders:
        conn = sqlite3.connect("users_bot.sql")
        cur = conn.cursor()
        cur.execute("SELECT order_id FROM orderss where user_id = '%d'" % (user_id))
        orders_id_of_this_user = cur.fetchall()
        if len(orders_id_of_this_user) > 0:
            for ord_id in orders_id_of_this_user:
                ord = getOrder(ord_id)
                if ord[0] == 'ACTIVE' and ord[2] == '0.01': # ord[0] - status, ord[2] - amount
                        return ord[1] # ord[1] - paylink
                else:
                    continue
        cur.close()
        conn.close()

    headers = {
        'Wpay-Store-Api-Key': 'IvTW7ArJ6wgxDIUUkD8Yu9XZjpHV8skzV5Jp',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    payload = {
        'amount': {
            'currencyCode': 'USD',  # выставляем счет в долларах USD
            'amount': '0.01',
        },
        'description': f'Subscription for {duration}',
        'externalId': f'{external_id}',  # ID счета на оплату в вашем боте
        'timeoutSeconds': 60*60,  # время действия счета в секундах
        'customerTelegramUserId': f'{user_id}',  # ID аккаунта Telegram покупателя
        'returnUrl': 'https://t.me/crypto_rise_bot',  # после успешной оплаты направить покупателя в наш бот
        'failReturnUrl': 'https://t.me/wallet',  # при отсутствии оплаты оставить покупателя в @wallet
    }
    external_id +=1

    response = requests.post(
        "https://pay.wallet.tg/wpay/store-api/v1/order",
        json=payload, headers=headers, timeout=10
    )

    data = response.json()

    if (response.status_code != 200) or (data['status'] not in ["SUCCESS", "ALREADY"]):
        return 'error'
    print(data)
    return [external_id, data['data']['id'], data['data']['payLink']]

def getOrder(order_id):
    headers = {
        'Wpay-Store-Api-Key': 'IvTW7ArJ6wgxDIUUkD8Yu9XZjpHV8skzV5Jp'
    }

    payload = {
        'id': f'{order_id}'
    }

    response = requests.get(
        url='https://pay.wallet.tg/wpay/store-api/v1/order/preview',
        params=payload, headers=headers
    )
    data = response.json()

    if (response.status_code != 200) or (data['status'] not in ["SUCCESS"]):
        return 'error'
    print(data)
    return [data['data']['status'], data['data']['payLink'], data['data']['amount']['amount']]

# print(getOrder(5590486413058))

#https://habr.com/ru/articles/751848/
app = Flask(__name__)
@app.route('/127.0.0.1:8080/wh', methods=['POST'])
def ipn_tgwallet():
    for event in request.get_json():
        if event["type"] == "ORDER_PAID":
            data = event["payload"]
            print("Оплачен счет N {} на сумму {} {}. Оплата {} {}.".format(
                data["externalId"],  # ID счета в вашем боте, который мы указывали при создании ссылки для оплаты
                data["orderAmount"]["amount"],  # Сумма счета, указанная при создании ссылки для оплаты
                data["orderAmount"]["currencyCode"],  # Валюта счета
                data["selectedPaymentOption"]["amount"]["amount"],  # Сколько оплатил покупатель
                data["selectedPaymentOption"]["amount"]["currencyCode"]  # В какой криптовалюте
            ))


    # нужно всегда возвращать код 200, чтобы WalletPay не делал повторных вызовов вебхука
    return 'OK'

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn2 = types.KeyboardButton("/help")
    btn1 = types.KeyboardButton("/plans")
    markup.row(btn1, btn2)
    mess = f'Hello, <b>{message.from_user.first_name}</b>!\nThis bot is designed to provide a tool for making money on cryptocurrency inter-exchange and intra-exchange arbitrage. By buying a subscription to the bot, you get access to chains. This will allow you to track coin rates on exchanges: buy cheaper on one exchange and sell more expensive on another.\nIf you want to look at the subscription plans, click on "/plans".\nClick on the "/help" button for information about all commands.'
    bot.send_message(message.chat.id, mess, reply_markup=markup, parse_mode='html')
    bot.send_message(message.chat.id, 'Before use, I recommend to familiarise yourself with the available commands', parse_mode='html')


@bot.message_handler(commands=['help'])
def help(message):
    mess = '/start - main information about this bot.\n/show_chains - command to show the chains\n/plans - subscription options for this bot.\n/subscription - command for those who have problems with subscription.\n/problem - command for those who have any problems with the bot.\n/admin - list of admin commands.'
    bot.send_message(message.chat.id, mess, parse_mode='html')


@bot.message_handler(commands=['admin'])
def admin(message):
    mess = '/input - command to add new user.\n/update - command to update user data.\n/delete - command to delete user by id.\n/show_users - command to show all users\n/reload - command to synchronized DB and Python code.'
    bot.send_message(message.chat.id, mess, parse_mode='html')


@bot.message_handler(commands=['show_chains'])
def show_chains(message):
    if id not in users and id not in admins:
        bot.send_message(message.chat.id, "Sorry you didn't subscribe")
    else:
        Response = ""
        with open('Links.txt', 'r') as links:
            for line in links:
                Response += line + '\n'
            mess = Response
            bot.send_message(message.chat.id, mess, parse_mode='html')


@bot.message_handler(commands=['plans'])
def plans(message):
    markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    markup1 = types.InlineKeyboardMarkup()
    btnWeek = types.InlineKeyboardButton(text='1 week', callback_data='1week')
    btnMonth = types.InlineKeyboardButton(text='1 month', callback_data='1month')
    btn6Month = types.InlineKeyboardButton(text='6 month', callback_data='6month')
    markup1.add(btnWeek).add(btnMonth).add(btn6Month)
    btnSub = types.KeyboardButton(text='/subscription')
    markup2.add(btnSub)
    mess1 = f'There are 3 subscription plans available in this bot.\n1 week - 50 USDT\n1 month - 150 USDT\n6 months - 600 USDT'
    mess2 = f'If for some reason you are unable to pay your subscription via Wallet click on /subscription'
    bot.send_message(message.chat.id, mess1, reply_markup=markup1, parse_mode='html')
    bot.send_message(message.chat.id, mess2, reply_markup=markup2, parse_mode='html')


@bot.message_handler(commands=['subscription']) # поменять работу
def subscription(message):
    mess1 = 'To pay for a subscription you can write to the admin. He will send you details for transfer. After payment you also need to send your id for entering into the database.'
    markup1 = types.InlineKeyboardMarkup()
    btnAdmin = types.InlineKeyboardButton(text='Admin', url='https://t.me/sea_gul1')
    btnId = types.InlineKeyboardButton(text='Get your id', callback_data='getId')
    markup1.row(btnId, btnAdmin)
    bot.send_message(message.chat.id, mess1, reply_markup=markup1, parse_mode='html')
    mess2 = 'After successful payment you can use the "Show chains" button.'
    markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btnChains = types.KeyboardButton(text='Show chains')
    markup2.add(btnChains)
    bot.send_message(message.chat.id, mess2, reply_markup=markup2, parse_mode='html')


@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    callbackData = callback.data
    global users, admins, orders
    if callbackData == 'getId':
        bot.send_message(callback.message.chat.id, f"Your id is `{callback.message.chat.id}`", parse_mode='MarkDown')
    elif callbackData == "1week" or callbackData == "1month" or callbackData == "6month":
        user_id = int(callback.message.chat.id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn = types.KeyboardButton(text='Show chains')
        markup.add(btn)
        if user_id in users or user_id in admins:
            bot.send_message(callback.message.chat.id, "You are already subscribed. Click the button to show the chains.", reply_markup=markup, parse_mode='html')
        else:
            start_date = datetime.now()
            if callbackData == '1week':
                duration = "1 week"
                call = 'after_pay_1week'
                ord = postOrder(50, duration, user_id)
            elif callbackData == '1month':
                duration = "1 month"
                call = 'after_pay_1month'
                ord = postOrder(150, duration, user_id)
            else:
                duration = "6 month"
                call = 'after_pay_6month'
                ord = postOrder(600, duration, user_id)
            if len(ord) != 1:
                cur_external_id = ord[0]
                order_id = ord[1]
                paylink = ord[2]
                conn = sqlite3.connect("users_bot.sql")
                cur = conn.cursor()
                cur.execute("INSERT INTO orderss (user_id, external_id, order_id, duration, start_date) VALUES ('%d', '%s', '%s', '%s', '%s')" % (user_id, cur_external_id, order_id, duration, start_date))
                conn.commit()
                cur.close()
                conn.close()
                orders.add(user_id)
            else:
                paylink = ord[0]
            btn2 = types.InlineKeyboardButton(text='Pay via Wallet', callback_data=call, url=paylink, pay=True)
            markup2 = types.InlineKeyboardMarkup()
            markup2.add(btn2)
            bot.send_message(callback.message.chat.id, "You can pay for your subscription using the button below.", reply_markup=markup2, parse_mode='html')

    elif callbackData == 'after_pay_1week' or callbackData == 'after_pay_1month' or callbackData == 'after_pay_6month':
        id = int(callback.message.chat.id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn = types.KeyboardButton(text='Show chains')
        markup.add(btn)
        if id in users or id in admins:
            bot.send_message(callback.message.chat.id, "You are already subscribed. Click the button to show the chains.", reply_markup=markup, parse_mode='html')
        else:
            username = '@' + callback.message.chat.username
            first_name = callback.message.chat.first_name
            duration = callbackData
            start_date = datetime.now()
            period = timedelta(1)
            if duration == "after_pay_1week":
                period = timedelta(7)
            elif duration == "after_pay_1month":
                period = timedelta(30)
            elif duration == "after_pay_6month":
                period = timedelta(180)
            end_of_date = start_date + period
            conn = sqlite3.connect("users_bot.sql")
            cur = conn.cursor()
            cur.execute("INSERT INTO users (id, username, first_name, start_date, duration, end_of_date) VALUES ('%d', '%s', '%s', '%s', '%s', '%s')" % (id, username, first_name, start_date, duration, end_of_date))
            conn.commit()
            # cur.execute('SELECT * FROM users')
            # usersSQL = cur.fetchall()
            # info = ''
            # for el in usersSQL:
            #     info += f'id = {el[0]}, username = @{el[1]}, first_name = {el[2]}, start_date = {el[3]}, duration = {el[4]}, end_of_date = {el[5]}\n'
            cur.close()
            conn.close()
            mess = f'Congrats! You are subscribed. Now you can use chains.'
            users.append(id)
            bot.send_message(callback.message.chat.id, mess, reply_markup=markup, parse_mode='html')


@bot.message_handler(commands=['show_users'])
def show_users(message):
    conn = sqlite3.connect("users_bot.sql")
    cur = conn.cursor()
    cur.execute('SELECT * FROM users')
    usersSQL = cur.fetchall()
    info = ''
    if len(usersSQL) > 0:
        for el in usersSQL:
            info += f'id = {el[0]}\nusername = {el[1]}\nfirst_name = {el[2]}\nstart_date = {el[3]}\nduration = {el[4]}\nend_of_date = {el[5]}\n'
        info += "\nIt's all info about users."
    else:
        info = 'Database is empty.'
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, info, parse_mode='html')



inputId = 0
inputUsername = ''
inputFirstname = ''
inputDuration = ''
@bot.message_handler(commands=['input'])
def input1(message):
    global admins
    if message.chat.id not in admins:
        bot.send_message(message.chat.id, "You are not admin", parse_mode='html')
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn = types.KeyboardButton(text='back')
        markup.add(btn)
        bot.send_message(message.chat.id, 'If you clicked here by accident and want to exit, write "back".', reply_markup=markup, parse_mode='html')
        bot.send_message(message.chat.id, 'Input user id', parse_mode='html')
        bot.register_next_step_handler(message, input2)


def reloadInput1(message):
    bot.send_message(message.chat.id, 'Input user id', parse_mode='html')
    bot.register_next_step_handler(message, input2)


def input2(message):
    global inputId
    text = str(message.text).strip().lower()
    if text == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    try:
        inputId = text
    except ValueError:
        bot.send_message(message.chat.id, 'You entered incorrect data.\nId should be integer.', parse_mode='html')
        reloadInput1(message)
        return
    if inputId in users:
        bot.send_message(message.chat.id, 'This user alredy in database', parse_mode='html')
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn = types.KeyboardButton(text='back')
    markup.add(btn)
    bot.send_message(message.chat.id, 'Input username', reply_markup=markup, parse_mode='html')
    bot.register_next_step_handler(message, input3)


def input3(message):
    global inputUsername
    inputUsername = '@' + str(message.text).strip()
    if inputUsername == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn = types.KeyboardButton(text='back')
    markup.add(btn)
    bot.send_message(message.chat.id, 'Input first_name', reply_markup=markup, parse_mode='html')
    bot.register_next_step_handler(message, input4)


def input4(message):
    global inputFirstname
    inputFirstname = str(message.text).strip()
    if inputFirstname == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn1 = types.KeyboardButton(text='1week')
    btn2 = types.KeyboardButton(text='1month')
    btn3 = types.KeyboardButton(text='6month')
    btn4 = types.KeyboardButton(text='back')
    markup.row(btn1, btn2)
    markup.row(btn3, btn4)
    bot.send_message(message.chat.id, 'Input duration of subscription', reply_markup=markup, parse_mode='html')
    bot.register_next_step_handler(message, input5)


def reloadInput4(message):
    bot.send_message(message.chat.id, 'Input duration of subscription\nExample: 1week / 1month / 6month', parse_mode='html')
    bot.register_next_step_handler(message, input5)


def input5(message):
    global inputId, inputUsername, inputFirstname, inputDuration
    inputDuration = str(message.text).strip()
    if inputDuration == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    if inputDuration == '1week' or inputDuration == '1month' or inputDuration == '6month':
        start_date = datetime.now()
        period = timedelta(1)
        if inputDuration == "1week":
            period = timedelta(7)
        elif inputDuration == "1month":
            period = timedelta(30)
        elif inputDuration == "6month":
            period = timedelta(180)
        end_of_date = start_date + period
        conn = sqlite3.connect("users_bot.sql")
        cur = conn.cursor()
        cur.execute("INSERT INTO users (id, username, first_name, start_date, duration, end_of_date) VALUES ('%d', '%s', '%s', '%s', '%s', '%s')" % (inputId, inputUsername, inputFirstname, start_date, inputDuration, end_of_date))
        conn.commit()
        users.append(inputId)
        cur.execute('SELECT * FROM users')
        usersSQL = cur.fetchall()
        info = ''
        for el in usersSQL:
            info += f'id = {el[0]}\nusername = {el[1]}\nfirst_name = {el[2]}\nstart_date = {el[3]}\nduration = {el[4]}\nend_of_date = {el[5]}\n'
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, f'User added successfully\n{info}', parse_mode='html')
    else:
        bot.send_message(message.chat.id, 'You entered incorrect data.\nDuration should be in this format: 1week / 1month / 6month', parse_mode='html')
        reloadInput4(message)
        return



@bot.message_handler(commands=['reload'])
def reload(message):
    global admins
    if message.chat.id not in admins:
        bot.send_message(message.chat.id, "You are not admin", parse_mode='html')
    else:
        conn = sqlite3.connect("users_bot.sql")
        cur = conn.cursor()
        cur.execute('SELECT * FROM users')
        usersSQL = cur.fetchall()
        if len(usersSQL) > 0:
            for el in usersSQL:
                users.append(int(el[0]))
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, "All users are upload", parse_mode='html')


updateId = 0
updateUsername= ''
updateFirstname = ''
updateDuration = ''
updateStartDate = datetime.now()
updateEndOfDate = datetime.now()
updateEl = ""
@bot.message_handler(commands=['update'])
def update1(message):
    messageChatId = message.chat.id
    global admins
    if message.chat.id not in admins:
        bot.send_message(message.chat.id, "You are not admin", parse_mode='html')
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn = types.KeyboardButton(text='back')
        markup.add(btn)
        bot.send_message(message.chat.id, 'If you clicked here by accident and want to exit, push "back".',reply_markup=markup, parse_mode='html')
        bot.send_message(message.chat.id, 'Enter the user id of the user whose data you want to update', parse_mode='html')
        bot.register_next_step_handler(message, update2)

def reloadUpdate1(message):
    bot.send_message(message.chat.id, 'Enter the user id of the user whose data you want to update', parse_mode='html')
    bot.register_next_step_handler(message, update2)

def update2(message):
    global updateId, updateEl
    text = str(message.text).strip().lower()
    if text == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    try:
        updateId = int(text)
    except ValueError:
        bot.send_message(message.chat.id, 'You entered incorrect data.\nId should be integer.', parse_mode='html')
        reloadUpdate1(message)
        return
    if len(users) != 0:
        if updateId in users:
            conn = sqlite3.connect("users_bot.sql")
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id = '%d'" % (updateId))
            usersSQL = cur.fetchall()
            updateEl = usersSQL[0]
            info = f'id = {updateEl[0]}\nusername = {updateEl[1]}\nfirst_name = {updateEl[2]}\nstart_date = {updateEl[3]}\nduration = {updateEl[4]}\nend_of_date = {updateEl[5]}\n'
            info += "\nIt's all info about this user"
            cur.close()
            conn.close()
            bot.send_message(message.chat.id, f"{info}", parse_mode='html')
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
            btn1 = types.KeyboardButton(text='username')
            btn2 = types.KeyboardButton(text='first_name')
            btn3 = types.KeyboardButton(text='duration')
            btn = types.KeyboardButton(text='back')
            markup.row(btn1, btn2)
            markup.row(btn3, btn)
            bot.send_message(message.chat.id, f"What would you like to change?",reply_markup=markup, parse_mode='html')
        else:
            bot.send_message(message.chat.id, f"User with id = {updateId} not found.", parse_mode='html')
            return
    else:
        bot.send_message(message.chat.id, f"Database is empty.", parse_mode='html')
        return
    bot.register_next_step_handler(message, update3)

def reloadUpdate3(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn1 = types.KeyboardButton(text='username')
    btn2 = types.KeyboardButton(text='first_name')
    btn3 = types.KeyboardButton(text='duration')
    btn = types.KeyboardButton(text='back')
    markup.row(btn1, btn2)
    markup.row(btn3, btn)
    bot.send_message(message.chat.id, f"What would you like to change?",reply_markup=markup, parse_mode='html')

def update3(message):
    text = str(message.text).strip().lower()
    if text == 'back':
        bot.send_message(message.chat.id, "You've successfully exited.", parse_mode='html')
        return
    elif text == 'username':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn = types.KeyboardButton(text='back')
        markup.add(btn)
        bot.send_message(message.chat.id, "Enter a new username with @", reply_markup=markup, parse_mode='html')
        bot.register_next_step_handler(message, updateUsernameFunc)
    elif text == 'first_name':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn = types.KeyboardButton(text='back')
        markup.add(btn)
        bot.send_message(message.chat.id, "Enter a new first_name.", reply_markup=markup, parse_mode='html')
        bot.register_next_step_handler(message, updateFirstnameFunc)
    elif text == 'duration':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn1 = types.KeyboardButton(text='1week')
        btn2 = types.KeyboardButton(text='1month')
        btn3 = types.KeyboardButton(text='6month')
        btn4 = types.KeyboardButton(text='back')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(message.chat.id, "Enter a new duration.", reply_markup=markup, parse_mode='html')
        bot.register_next_step_handler(message, updateDurationFunc)
    else:
        bot.send_message(message.chat.id, "You input incorrect data.", parse_mode='html')
        reloadUpdate3(message)
        return

def updateUsernameFunc(message):
    global updateUsername, updateId
    text = str(message.text).strip()
    if text.lower() == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    else:
        updateUsername = text
        conn = sqlite3.connect("users_bot.sql")
        cur = conn.cursor()
        cur.execute("UPDATE users SET username = '%s' WHERE id = '%d'" % (updateUsername, updateId))
        conn.commit()
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, "Username successfully changed", parse_mode='html')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn1 = types.KeyboardButton(text='yes')
        btn2 = types.KeyboardButton(text='no')
        markup.row(btn1, btn2)
        bot.send_message(message.chat.id, "Anything else you'd like to change?", reply_markup=markup, parse_mode='html')
        bot.register_next_step_handler(message, update4)

def updateFirstnameFunc(message):
    global updateFirstname, updateId
    text = str(message.text).strip()
    if text.lower() == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    else:
        updateFirstname = text
        conn = sqlite3.connect("users_bot.sql")
        cur = conn.cursor()
        cur.execute("UPDATE users SET first_name = '%s' WHERE id = '%d'" % (updateFirstname, updateId))
        conn.commit()
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, "First_name successfully changed", parse_mode='html')
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn1 = types.KeyboardButton(text='yes')
        btn2 = types.KeyboardButton(text='no')
        markup.row(btn1, btn2)
        bot.send_message(message.chat.id, "Anything else you'd like to change?",reply_markup=markup, parse_mode='html')
        bot.register_next_step_handler(message, update4)

def reloadUpdateDuration(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn1 = types.KeyboardButton(text='1week')
    btn2 = types.KeyboardButton(text='1month')
    btn3 = types.KeyboardButton(text='6month')
    btn4 = types.KeyboardButton(text='back')
    markup.row(btn1, btn2)
    markup.row(btn3, btn4)
    bot.send_message(message.chat.id, "Enter a new duration.", reply_markup=markup, parse_mode='html')
    bot.register_next_step_handler(message, updateDuration)

def updateDurationFunc(message):
    global updateDuration
    text = str(message.text).strip().lower()
    if text == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    elif text == '1week' or text == '1month' or text == '6month':
        updateDuration = text
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn1 = types.KeyboardButton(text='yes')
        btn2 = types.KeyboardButton(text='no')
        btn3 = types.KeyboardButton(text='back')
        markup.row(btn1, btn2)
        markup.row(btn3)
        bot.send_message(message.chat.id, "Do you want to change the start_date?",reply_markup=markup, parse_mode='html')
        bot.register_next_step_handler(message, updateDuration2)
    else:
        bot.send_message(message.chat.id, 'You entered incorrect data.\nDuration should be in this format: 1week / 1month / 6month', parse_mode='html')
        reloadUpdateDuration(message)
        return

def reloadUpdateDuration2(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn1 = types.KeyboardButton(text='yes')
    btn2 = types.KeyboardButton(text='no')
    btn3 = types.KeyboardButton(text='back')
    markup.row(btn1, btn2)
    markup.row(btn3)
    bot.send_message(message.chat.id, "Do you want to change the start_date?", reply_markup=markup, parse_mode='html')
    bot.register_next_step_handler(message, updateDuration2)

def updateDuration2(message):
    global updateDuration, updateStartDate, updateEndOfDate, updateEl, updateId
    text = str(message.text).strip().lower()
    if text == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    elif text == 'y' or text == 'yes' or text == 'da' or text == 'да' or text =='+':
        updateStartDate = datetime.now()
        period = timedelta(1)
        if updateDuration == "1week":
            period = timedelta(7)
        elif updateDuration == "1month":
            period = timedelta(30)
        elif updateDuration == "6month":
            period = timedelta(180)
        updateEndOfDate = updateStartDate + period
        conn = sqlite3.connect("users_bot.sql")
        cur = conn.cursor()
        cur.execute("UPDATE users SET start_date = '%s', duration = '%s', end_of_date = '%s' WHERE id = '%d'" % (updateStartDate, updateDuration, updateEndOfDate, updateId))
        conn.commit()
        cur.close()
        conn.close()
    elif text == 'n' or text == 'no' or text == 'net' or text == 'нет' or text == '-':
        updateStartDate = datetime.strptime(str(updateEl[3]), '%Y-%m-%d %H:%M:%S.%f')
        period = timedelta(1)
        if updateDuration == "1week":
            period = timedelta(7)
        elif updateDuration == "1month":
            period = timedelta(30)
        elif updateDuration == "6month":
            period = timedelta(180)
        updateEndOfDate = updateStartDate + period
        conn = sqlite3.connect("users_bot.sql")
        cur = conn.cursor()
        cur.execute("UPDATE users SET duration = '%s', end_of_date = '%s' WHERE id = '%d'" % (updateDuration, updateEndOfDate, updateId))
        conn.commit()
        cur.close()
        conn.close()
    else:
        bot.send_message(message.chat.id, "Please write\ny / yes / da / да / +\nor\nn / no / net / нет / -", parse_mode='html')
        reloadUpdateDuration2(message)
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn1 = types.KeyboardButton(text='yes')
    btn2 = types.KeyboardButton(text='no')
    btn3 = types.KeyboardButton(text='back')
    markup.row(btn1, btn2)
    markup.row(btn3)
    bot.send_message(message.chat.id, "Anything else you'd like to change?",reply_markup=markup, parse_mode='html')
    bot.register_next_step_handler(message, update4)

def reloadUpdate4(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn1 = types.KeyboardButton(text='yes')
    btn2 = types.KeyboardButton(text='no')
    btn3 = types.KeyboardButton(text='back')
    markup.row(btn1, btn2)
    markup.row(btn3)
    bot.send_message(message.chat.id, "Anything else you'd like to change?", reply_markup=markup, parse_mode='html')
    bot.register_next_step_handler(message, update4)

def update4(message):
    text = str(message.text).strip().lower()
    if text == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    elif text == 'y' or text == 'yes' or text == 'da' or text == 'да' or text =='+':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn1 = types.KeyboardButton(text='username')
        btn2 = types.KeyboardButton(text='first_name')
        btn3 = types.KeyboardButton(text='duration')
        btn = types.KeyboardButton(text='back')
        markup.row(btn1, btn2)
        markup.row(btn3, btn)
        bot.send_message(message.chat.id, f"What would you like to change?", reply_markup=markup, parse_mode='html')
        bot.register_next_step_handler(message, update3)
    elif text == 'n' or text == 'no' or text == 'net' or text == 'нет' or text == '-':
        update5(message)
    else:
        bot.send_message(message.chat.id, "Please write\ny / yes / da / да / +\nor\nn / no / net / нет / -", parse_mode='html')
        reloadUpdate4(message)
        return

def update5(message):
    global updateId
    conn = sqlite3.connect("users_bot.sql")
    cur = conn.cursor()
    # cur.execute("DELETE FROM users WHERE id = '%d'" % (updateId))
    # conn.commit()
    # cur.execute("INSERT INTO users (id, username, first_name, start_date, duration, end_of_date) VALUES ('%d', '%s', '%s', '%s', '%s', '%s')" % (updateId, updateUsername, updateFirstname, updateStartDate, updateDuration, updateEndOfDate))
    # conn.commit()
    cur.execute("SELECT * FROM users WHERE id = '%d'" % (updateId))
    usersSQL = cur.fetchall()
    el = usersSQL[0]
    info = f'id = {el[0]}\nusername = {el[1]}\nfirst_name = {el[2]}\nstart_date = {el[3]}\nduration = {el[4]}\nend_of_date = {el[5]}\n'
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, f"User is updated successfully\nNew info about him:{info}\n", parse_mode='html')



deleteId = 0
@bot.message_handler(commands=['delete'])
def delete1(message):
    global admins
    if message.chat.id not in admins:
        bot.send_message(message.chat.id, "You are not admin", parse_mode='html')
    else:
        bot.send_message(message.chat.id, 'If you clicked here by accident and want to exit, write "back".', parse_mode='html')
        bot.send_message(message.chat.id, 'To delete a user, enter their id', parse_mode='html')
        bot.register_next_step_handler(message, delete2)

def reloadDelete1(message):
    bot.send_message(message.chat.id, 'To delete a user, enter their id', parse_mode='html')
    bot.register_next_step_handler(message, delete2)

def delete2(message):
    global deleteId
    text = str(message.text).strip().lower()
    if text == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    try:
        deleteId = int(text)
    except ValueError:
        bot.send_message(message.chat.id, 'You entered incorrect data.\nId should be integer.', parse_mode='html')
        reloadDelete1(message)
        return
    bot.send_message(message.chat.id, 'Are you sure to delete this user?', parse_mode='html')
    bot.register_next_step_handler(message, delete3)

def reloadDelete2(message):
    bot.send_message(message.chat.id, 'Are you sure to delete this user?', parse_mode='html')
    bot.register_next_step_handler(message, delete3)

def delete3(message):
    global deleteId, users
    text = str(message.text).strip().lower()
    if text == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    elif text == 'y' or text == 'yes' or text == 'da' or text == 'да' or text =='+':
        if len(users) != 0:
            if deleteId in users:
                conn = sqlite3.connect("users_bot.sql")
                cur = conn.cursor()
                cur.execute("DELETE FROM users WHERE id = '%d'" % (deleteId))
                conn.commit()
                users.remove(deleteId)
                cur.close()
                conn.close()
                bot.send_message(message.chat.id, f"User with id = {deleteId} deleted.", parse_mode='html')
            else:
                bot.send_message(message.chat.id, f"User with id = {deleteId} not found.", parse_mode='html')
                return
        else:
            bot.send_message(message.chat.id, f"Database is empty.", parse_mode='html')
            return
    elif text == 'n' or text == 'no' or text == 'net' or text == 'нет' or text == '-':
        bot.send_message(message.chat.id, "Nobody deleted.", parse_mode='html')
        return
    else:
        bot.send_message(message.chat.id, "Please write\ny / yes / da / да / +\nor\nn / no / net / нет / -", parse_mode='html')
        reloadDelete2(message)
        return



@bot.message_handler(commands=['problem'])
def problem(message):
    bot.send_message(message.chat.id, 'Please describe your problem in one message and send it to this chat. Soon admin will contact you and try to solve your problem.\nIf you clicked here by accident and want to exit, write "back".', parse_mode='html')
    bot.register_next_step_handler(message, handTheProblemAndSendToAdmin)

def handTheProblemAndSendToAdmin(message):
    username = message.chat.username
    text = str(message.text)
    if text == 'back':
        bot.send_message(message.chat.id, "You've successfully exited", parse_mode='html')
        return
    bot.send_message(350591707, f'<b>We have a problem!</b>\n@{username}\n{text}', parse_mode='html')
    bot.send_message(574752230, f'<b>We have a problem!</b>\n@{username}\n{text}', parse_mode='html')
    bot.send_message(message.chat.id, 'Your message have been send to admin.', parse_mode='html')



@bot.message_handler(content_types=['text'])
def getTextMessages(message):
    global users, admins
    id = int(message.chat.id)
    if str(message.text).strip().lower() == "plans" or str(message.text).strip().lower() == "plan":
        markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        markup1 = types.InlineKeyboardMarkup()
        btnWeek = types.InlineKeyboardButton(text='1 week', callback_data='1week')
        btnMonth = types.InlineKeyboardButton(text='1 month', callback_data='1month')
        btn6Month = types.InlineKeyboardButton(text='6 month', callback_data='6month')
        markup1.add(btnWeek).add(btnMonth).add(btn6Month)
        btnSub = types.KeyboardButton(text='/subscription')
        markup2.add(btnSub)
        mess1 = f'There are 3 subscription plans available in this bot.\n1 week - 25 USDT\n1 month - 50 USDT\n6 months - 200 USDT'
        mess2 = f'If for some reason you are unable to pay your subscription via Wallet click on /subscription'
        bot.send_message(message.chat.id, mess1, reply_markup=markup1, parse_mode='html')
        bot.send_message(message.chat.id, mess2, reply_markup=markup2, parse_mode='html')
    elif str(message.text).strip().lower() == "subscription":
        mess1 = 'To pay for a subscription you can write to the admin. He will send you details for transfer. After payment you also need to send your id for entering into the database.'
        markup1 = types.InlineKeyboardMarkup()
        btnAdmin = types.InlineKeyboardButton(text='Admin', url='https://t.me/sea_gul1')
        btnId = types.InlineKeyboardButton(text='Get your id', callback_data='getId')
        markup1.row(btnId, btnAdmin)
        bot.send_message(message.chat.id, mess1, reply_markup=markup1, parse_mode='html')
        mess2 = 'After successful payment you can use the "Show chains" button.'
        markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btnChains = types.KeyboardButton(text='Show chains')
        markup2.add(btnChains)
        bot.send_message(message.chat.id, mess2, reply_markup=markup2, parse_mode='html')
    elif str(message.text).strip().lower() == "help":
        mess = '/start - main information about this bot.\n/show_chains - command to show the chains\n/plans - subscription options for this bot.\n/subscription - command for those who have problems with subscription.\n/problem - command for those who have any problems with the bot.\n/admin - list of admin commands.'
        bot.send_message(message.chat.id, mess, parse_mode='html')
    elif str(message.text).strip().lower() == "show users" or str(message.text).strip().lower() == "show user":
        conn = sqlite3.connect("users_bot.sql")
        cur = conn.cursor()
        cur.execute('SELECT * FROM users')
        usersSQL = cur.fetchall()
        info = ''
        if len(usersSQL) > 0:
            for el in usersSQL:
                info += f'id = {el[0]}\nusername = {el[1]}\nfirst_name = {el[2]}\nstart_date = {el[3]}\nduration = {el[4]}\nend_of_date = {el[5]}\n'
            info += "\nIt's all info about users."
        else:
            info = 'Database is empty.'
        cur.close()
        conn.close()
        bot.send_message(message.chat.id, info, parse_mode='html')
    elif str(message.text).strip().lower() == "show chains" or str(message.text).strip().lower() == "show chain" or str(message.text).strip().lower() == "chain" or str(message.text).strip().lower() == "chains":
        if id not in users and id not in admins:
            bot.send_message(message.chat.id, "Sorry you didn't subscribe")
        else:
            Response = ""
            with open('Links.txt', 'r') as links:
                for line in links:
                    Response += line + '\n'
                mess = Response
                bot.send_message(message.chat.id, mess, parse_mode='html')


bot.polling(none_stop = True, interval=0)