import aiogram.utils.exceptions
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import WalletPay.types.Exception
import sqlite3
from datetime import datetime, timedelta
from WalletPay import WalletPayAPI, WebhookManager
from WalletPay.types import Event
import asyncio

from typing import List, Union
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware



bot = Bot(token='YOUR_TOKEN')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
api = WalletPayAPI(api_key='YOUR_PAYMENT_TOKEN')
wm = WebhookManager(client=api)

users = [] # Динамический массив хранящий id текущих пользователей
orders = set() # Множество, хранящее id ордеров
admins = [] # Статический массив с id администраторов




conn = sqlite3.connect("users_bot.sql")
cur = conn.cursor()
# cur.execute('DROP TABLE IF EXISTS users')
# cur.execute('CREATE TABLE users (id int primary key, username varchar(50), first_name varchar(50),start_date datetime, duration varchar(10), end_of_date datetime)')
cur.execute('CREATE TABLE IF NOT EXISTS users (id int primary key, username varchar(50), first_name varchar(50),start_date datetime, duration varchar(10), end_of_date datetime)')
conn.commit()
# cur.execute('DROP TABLE IF EXISTS orderss')
cur.execute('CREATE TABLE IF NOT EXISTS orderss (external_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id int, username varchar(50), first_name varchar(50), order_id varchar(20), duration varchar(10), start_date datetime)')
conn.commit()

cur.execute('SELECT * FROM users') # Заполнение массива users пользователями из базы данных
usersSQL = cur.fetchall()
if len(usersSQL) > 0:
    for el in usersSQL:
        users.append(int(el[0]))
cur.execute('SELECT * FROM orderss') # Заполнение множества orders пользователями из базы данных
ordersSQL = cur.fetchall()
if len (ordersSQL) > 0:
    for el in ordersSQL:
        orders.add(int(el[1]))
cur.close()
conn.close()

class AlbumMiddleware(BaseMiddleware):

    album_data: dict = {}

    def __init__(self, latency: Union[int, float] = 0.01):
        self.latency = latency
        super().__init__()

    async def on_process_message(self, message: types.Message, data: dict):
        if not message.media_group_id:
            return

        try:
            self.album_data[message.media_group_id].append(message)
            raise CancelHandler()  # Tell aiogram to cancel handler for this group element
        except KeyError:
            self.album_data[message.media_group_id] = [message]
            await asyncio.sleep(self.latency)

            message.conf["is_last"] = True
            data["album"] = self.album_data[message.media_group_id]

    async def on_post_process_message(self, message: types.Message, result: dict, data: dict):
        if message.media_group_id and message.conf.get("is_last"):
            del self.album_data[message.media_group_id]


def createOrder(amount, duration, user_id, username, first_name): # При полном доступе к Wallet надо учитывать amount
    global orders
    conn = sqlite3.connect("users_bot.sql")
    cur = conn.cursor()
    if user_id in orders:
        cur.execute("SELECT order_id FROM orderss where user_id = '%d'" % (user_id))
        orders_id_of_this_user = cur.fetchall()
        if len(orders_id_of_this_user) > 0:
            for ord_id in orders_id_of_this_user:
                if ord_id[0] == '-':
                    continue
                ord = api.get_order_preview(order_id=ord_id[0])
                if ord.status == "ACTIVE" and ord.amount.amount == '0.01': # Заменить 0.01 на amount
                    cur.close()
                    conn.close()
                    return [ord.pay_link]
                else:
                    continue
    order_api = ''
    while True:
        start_date = datetime.now()
        cur.execute("INSERT INTO orderss (user_id, username, first_name, order_id, duration, start_date) VALUES ('%d', '%s', '%s', '%s', '%s', '%s')" % (user_id, username, first_name, '-', duration, start_date))
        conn.commit()
        cur.execute("SELECT external_id FROM orderss WHERE  user_id = '%d' and duration = '%s' and start_date = '%s'" % (user_id, duration, start_date))
        curr_external_id = str(cur.fetchall()[0])[1:-2]
        orders.add(user_id)
        try:
            order_api = api.create_order(
                currency_code='USD',
                amount=0.01, # Заменить 0.01 на amount
                description=f'Supscription for {duration}',
                external_id=curr_external_id,
                timeout_seconds=60*60,
                customer_telegram_user_id=f'{user_id}',
                fail_return_url='https://t.me/wallet',
                return_url='https://t.me/crypto_rise_bot'
            )
            cur.close()
            conn.close()
            break
        except WalletPay.types.Exception.WalletPayException:
            continue
    return [order_api.id, order_api.pay_link, start_date]


@wm.successful_handler() # Поставить на хост с SSL и проверить работоспособность
async def handle_successful_event(event: Event):
    # Handle successful payment event
    user_id = event.event_id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn = types.KeyboardButton(text='Show chains')
    markup.add(btn)
    if user_id in users or user_id in admins:
        await bot.send_message(user_id, "You are already subscribed. Click the button to show the chains.", reply_markup=markup, parse_mode='html')
    else:
        order_id = event.payload.order_id
        conn = sqlite3.connect("users_bot.sql")
        cur = conn.cursor()
        cur.execute("SELECT username, first_name, duration FROM orderss WHERE user_id = '%d' and order_id = '%s'" % (user_id, order_id))
        ord = cur.fetchall()[0]
        username = ord[0]
        first_name = ord[1]
        duration = ord[2]
        start_date = datetime.now()
        period = timedelta(1)
        if duration == "after_pay_1week":
            period = timedelta(7)
        elif duration == "after_pay_1month":
            period = timedelta(30)
        elif duration == "after_pay_6month":
            period = timedelta(180)
        end_of_date = start_date + period
        cur.execute("INSERT INTO users (id, username, first_name, start_date, duration, end_of_date) VALUES ('%d', '%s', '%s', '%s', '%s', '%s')" % (id, username, first_name, start_date, duration, end_of_date))
        conn.commit()
        cur.close()
        conn.close()
        cur.close()
        conn.close()
        mess = f'Congrats! You are subscribed. Now you can use chains.'
        users.append(user_id)
        await bot.send_message(user_id, mess, reply_markup=markup, parse_mode='html')

@wm.failed_handler() # Поставить на хост с SSL и проверить работоспособность
async def handle_failed_event(event: Event):
    # Handle failed payment event
    user_id = "USER_ID"
    await bot.send_message(chat_id=user_id, text=f"Your payment for order {event.payload.order_id} failed. Please try again.")


async def on_startup(dp):
    await bot.send_message(chat_id=admins[0], text="Bot has started!")
    # Start the webhook manager in the background
    asyncio.create_task(wm.start())

async def on_shutdown(dp):
    await bot.send_message(chat_id=admins[0], text="Bot is shutting down!")


@dp.message_handler(commands=['start']) # Сделать нормальное описание
async def start(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    btn2 = types.KeyboardButton("/help")
    btn1 = types.KeyboardButton("/plans")
    markup.row(btn1, btn2)
    mess = f'Hello, <b>{message.from_user.first_name}</b>!\nThis bot is designed to provide a tool for making money on cryptocurrency intra-exchange arbitrage. By buying a subscription to the bot, you get access to chains. This will allow you to track coin rates on exchanges: buy cheaper on one exchange and sell more expensive on another.\nIf you want to look at the subscription plans, click on "/plans".\nClick on the "/help" button for information about all commands.'
    await message.answer(text=mess, reply_markup=markup, parse_mode='html')
    await message.answer(text='Before use, I recommend to familiarise yourself with the available commands')


@dp.message_handler(commands=['help'])  # Сделать нормальное описание
async def help(message: types.Message):
    mess = '/start - main information about this bot.\n/show_chains - command to show the chains\n/plans - subscription options for this bot.\n/subscription - command for those who have problems with subscription.\n/problem - command for those who have any problems with the bot.\n/admin - list of admin commands.'
    await message.answer(text=mess)


@dp.message_handler(commands=['admin']) # Обновить команды
async def admin(message: types.Message):
    mess = '/input - command to add new user.\n/update - command to update user data.\n/delete - command to delete user by id.\n/show_users - command to show all users\n/reload - command to synchronized DB and Python code.'
    await message.answer(text=mess)


@dp.message_handler(commands=['show_chains'])
async def show_chains(message: types.Message):
    global users, admins
    id = message.chat.id
    if id not in users and id not in admins:
        await message.answer(text="Sorry you didn't subscribe")
    else:
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton(text='reload chains', callback_data='reload_chains')
        markup.add(btn)
        Response = ""
        with open('Links.txt', 'r') as links:
            for line in links:
                Response += line + '\n'
            mess = Response
            await message.answer(text=mess, reply_markup=markup, parse_mode='html')
            await bot.delete_message(id, message.message_id - 1)
            await bot.delete_message(id, message.message_id)


@dp.message_handler(commands=['plans'])
async def plans(message: types.Message):
    markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1, one_time_keyboard=True)
    markup1 = types.InlineKeyboardMarkup()
    btnWeek = types.InlineKeyboardButton(text='1 week', callback_data='1week')
    btnMonth = types.InlineKeyboardButton(text='1 month', callback_data='1month')
    btn6Month = types.InlineKeyboardButton(text='6 month', callback_data='6month')
    markup1.add(btnWeek).add(btnMonth).add(btn6Month)
    btnSub = types.KeyboardButton(text='/subscription')
    markup2.add(btnSub)
    mess1 = f'There are 3 subscription plans available in this bot.\n1 week - 50 USDT\n1 month - 150 USDT\n6 months - 600 USDT'
    mess2 = f'If for some reason you are unable to pay your subscription via Wallet click on /subscription'
    await message.answer(text=mess1, reply_markup=markup1)
    await message.answer(text=mess2, reply_markup=markup2)



@dp.callback_query_handler()
async def callback_message(callback):
    callbackData = callback.data
    global users, admins, orders
    user_id = int(callback.message.chat.id)
    if callbackData == 'reload_chains':
        if user_id not in users and user_id not in admins:
            await bot.send_message(callback.message.chat.id, "Sorry you didn't subscribe")
        else:
            markup = types.InlineKeyboardMarkup()
            btn = types.InlineKeyboardButton(text='reload chains', callback_data='reload_chains')
            markup.add(btn)
            Response = ""
            with open('Links.txt', 'r') as links:
                for line in links:
                    Response += line + '\n'
                mess = Response
                await bot.send_message(user_id, mess, reply_markup=markup, parse_mode='html')
                await bot.delete_message(user_id, callback.message.message_id)
    elif callbackData == "1week" or callbackData == "1month" or callbackData == "6month":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
        btn = types.KeyboardButton(text='Show chains')
        markup.add(btn)
        if user_id in users or user_id in admins:
            await callback.message.answer(text="You are already subscribed. Click the button to show the chains.", reply_markup=markup)
        else:
            username = callback.message.chat.username
            first_name = callback.message.chat.first_name
            if callbackData == '1week':
                duration = "1 week"
                ord = createOrder(50, duration, user_id, username, first_name)
            elif callbackData == '1month':
                duration = "1 month"
                ord = createOrder(150, duration, user_id, username, first_name)
            else:
                duration = "6 month"
                ord = createOrder(600, duration, user_id, username, first_name)
            if len(ord) != 1:
                order_id = ord[0]
                paylink = ord[1]
                start_date = ord[2]
                conn = sqlite3.connect("users_bot.sql")
                cur = conn.cursor()
                cur.execute("UPDATE orderss SET order_id = '%s' WHERE user_id = '%d' and duration = '%s' and start_date = '%s'" % (order_id, user_id, duration, start_date))
                conn.commit()
                cur.close()
                conn.close()
            else:
                paylink = ord[0]
            btn2 = types.InlineKeyboardButton(text='Pay via Wallet', url=paylink, pay=True)
            markup2 = types.InlineKeyboardMarkup()
            markup2.add(btn2)
            await callback.message.answer(text="You can pay for your subscription using the button below.", reply_markup=markup2)


@dp.message_handler(commands=['show_users'])
async def show_users(message: types.Message):
    global admins
    if message.message_id not in admins:
        await message.answer(text="You are not admin")
    else:
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
        await message.answer(text=info)


@dp.message_handler(commands=['reload']) # Возможно добавить проверку на истечение времени подписки
async def reload(message: types.Message):
    global admins
    if message.message_id not in admins:
        await message.answer(text="You are not admin")
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
        await message.answer(text="All users are upload")


class Form(StatesGroup):
    problem = State()
    reply_id = State()
    answer = State()
    delete_id = State()
    delete_id_answer = State()
    update_id = State()
    field_change = State()
    update_username = State()
    update_firstname = State()
    update_duration = State()
    update_answer = State()
    update_start_date = State()
    update_end_date = State()
    payment_address = State()
    payment_screenshot = State()
    payment_id = State()
    payment_answer = State()
    input_id = State()
    input_firstname = State()
    input_username = State()
    input_duration = State()


from aiogram.types import InputFile
qr = InputFile('qr.jpg')
@dp.message_handler(commands=['subscription'])
async def subscription(message: types.Message):
    mess1 = 'If you have trouble paying via Wallet, you can send the subscription price in USDT (TRC20) currency to this address.\n`TAVvvzzS1357spwmaC9sLFVmwtKfJiddkN`\nOr use this qr-code:'
    mess2 = 'To confirm the payment you need a <u><b>screenshot</b></u> of the transfer and the <u><b>USDT address</b></u> from where the transfer was made.\nAfter successful payment, click on the button below.'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    btn = types.KeyboardButton(text='/payment_confirmation')
    markup.add(btn)
    await message.answer(text=mess1, parse_mode='Markdown')
    await message.answer_photo(photo=qr)
    await message.answer(text=mess2, reply_markup=markup, parse_mode='html')



@dp.message_handler(commands=['payment_confirmation'])
async def confirm_payment(message: types.Message):
    await message.answer(text='Please send your USDT address.')
    await Form.payment_address.set()

@dp.message_handler(lambda message: not message.text.isalnum(), state=Form.payment_address)
async def payment_adress_invalid(message: types.Message):
    return await message.reply("You input incorrect address.\nInput it correctly again.")

@dp.message_handler(lambda message: message.text.isalnum(), state=Form.payment_address)
async def payment_adress_successful(message: types.Message, state: FSMContext):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited.")
        return
    async with state.proxy() as data:
        data['payment_address'] = message.text
    await message.answer(text='Please send screenshot of successful crypto transfer.')
    await Form.payment_screenshot.set()

@dp.message_handler(lambda message: len(message.photo) == 0, state=Form.payment_screenshot, content_types=['text'])
async def payment_screenshot_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited.")
        return
    return await message.reply("You don't send screenshot.\nInput it correctly again.")

@dp.message_handler(lambda message: len(message.photo) > 0, state=Form.payment_screenshot, is_media_group=True, content_types=types.ContentType.PHOTO)
async def payment_screenshot_successful(message: types.Message, album: List[types.Message], state: FSMContext):
    address = ''
    async with state.proxy() as data:
        data['payment_screenshot'] = message.photo
        address = data['payment_address']
    media_group = types.MediaGroup()
    for obj in album:
        if obj.photo:
            file_id = obj.photo[-1].file_id
        else:
            file_id = obj[obj.content_type].file_id
        try:
            media_group.attach({"media": file_id, "type": obj.content_type})
        except ValueError:
            return await message.answer("This type of album is not supported.")
    for id in admins:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
        btn = types.KeyboardButton(text='/reply_to_payment')
        markup.add(btn)
        await bot.send_message(id, text='<b>We have a successful payment!</b>', parse_mode='html')
        await bot.send_message(id, text=f'Message from user\n@{message.from_user.username}\nid = `{message.chat.id}`\n\nAddress:\n`{address}`\nPhoto:', parse_mode='MarkDown')
        await bot.send_media_group(id, media=media_group)
        await bot.send_message(id, text="Don't forget to check payment of this user.\nUse /input and /reply_to_payment")
        await state.finish()
    await message.answer(text='Your data send to admin successfully. Soon he will answer you.')



@dp.message_handler(commands=['reply_to_payment'])
async def reply_payment(message: types.Message):
    global admins
    if message.chat.id not in admins:
        await message.answer("You are not admin")
    else:
        await message.answer('If you clicked here by accident and want to exit, write "exit".')
        await message.answer('Enter the id of the user to whom you want to reply.')
        await Form.payment_id.set()

@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.payment_id)
async def payment_id_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    return await message.reply("Id gotta be integer.\nInput id again (digits only)")

@dp.message_handler(lambda message: message.text.isdigit(), state=Form.payment_id)
async def payment_id_successful(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['payment_id'] = int(message.text)
    await message.answer("Input your answer.")
    await Form.payment_answer.set()

@dp.message_handler(state=Form.payment_answer)
async def payment_answer(message: types.Message, state: FSMContext):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await state.finish()
        await message.answer(text="You've successfully exited")
        return
    async with state.proxy() as data:
        data['payment_answer'] = message.text
        try:
            await bot.send_message(data['payment_id'], text='<b>Answer from admin:</b>\n' + data['payment_answer'], parse_mode='html')
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
            btn1 = types.KeyboardButton(text='/problem')
            btn2 = types.KeyboardButton(text='/show_chains')
            markup.add(btn1, btn2)
            await bot.send_message(data['payment_id'], text='If you have some problem use /problem\nIf your payment was successful you cam use button /show_chain', reply_markup=markup, parse_mode='html')
            await message.reply(text='Message send successfully')
            await state.finish()
        except aiogram.utils.exceptions.ChatNotFound:
            await message.answer(text='Chat not found.\nTry /reply_to_problem again')
            await state.finish()
            return



@dp.message_handler(commands=['problem'])
async def problem(message: types.Message):
    await message.answer(text='Please describe your problem in one message and send it to this chat. Soon admin will contact you and try to solve your problem.\nIf you clicked here by accident and want to exit, write "back".')
    await Form.problem.set()

@dp.message_handler(state=Form.problem)
async def handTheProblemAndSendToAdmin(message: types.Message, state: FSMContext):
    global admins
    async with state.proxy() as data:
        data['problem'] = message.text
    text = message.text
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        await state.finish()
        return
    for id in admins:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
        btn = types.KeyboardButton(text='/reply_to_problem')
        markup.add(btn)
        await bot.send_message(id, text='<b>We have a problem!</b>', parse_mode='html')
        await bot.send_message(id, text=f'Message from user\n@{message.from_user.username}\nid = `{message.chat.id}`\n\nProblem:\n{text}', parse_mode='MarkDown')
        await bot.send_message(id, text='Use /reply_to_problem')
    await state.finish()
    await message.answer(text='Your message have been send to admin. You will get an answer soon.')



@dp.message_handler(commands=['reply_to_problem'])
async def reply(message: types.Message):
    global admins
    if message.chat.id not in admins:
        await message.answer("You are not admin")
    else:
        await message.answer('If you clicked here by accident and want to exit, write "exit".')
        await message.answer('Enter the id of the user to whom you want to reply.')
        await Form.reply_id.set()

@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.reply_id)
async def reply_id_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    return await message.reply("Id gotta be integer.\nInput id again (digits only)")

@dp.message_handler(lambda message: message.text.isdigit(), state=Form.reply_id)
async def reply_id_successful(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['reply_id'] = int(message.text)
    await message.answer("Input your answer.")
    await Form.answer.set()

@dp.message_handler(state=Form.answer)
async def answer(message: types.Message, state: FSMContext):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await state.finish()
        await message.answer(text="You've successfully exited")
        return
    async with state.proxy() as data:
        data['answer'] = message.text
        try:
            await bot.send_message(data['reply_id'], text='<b>Answer from admin:</b>\n' + data['answer'], parse_mode='html')
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
            btn = types.KeyboardButton(text='/problem')
            markup.add(btn)
            await bot.send_message(data['reply_id'], text='If you want to send something again use /problem', reply_markup=markup, parse_mode='html')
            await message.reply(text='Message send successfully')
            await state.finish()
        except aiogram.utils.exceptions.ChatNotFound:
            await message.answer(text='Chat not found.\nTry /reply_to_problem again')
            await state.finish()
            return



@dp.message_handler(commands=['input'])
async def input(message: types.Message):
    global admins
    if message.chat.id not in admins:
        await message.answer(text="You are not admin")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn = types.KeyboardButton(text='exit')
        markup.add(btn)
        await message.answer(text='If you clicked here by accident and want to exit, write "exit".', reply_markup=markup, parse_mode='html')
        await bot.send_message(message.chat.id, 'Input user id', parse_mode='html')
        await Form.input_id.set()

@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.input_id)
async def input_id_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    return await message.reply("Id gotta be integer.\nInput id again (digits only)")

@dp.message_handler(lambda message: message.text.isdigit(), state=Form.input_id)
async def input_id_successful(message: types.Message, state: FSMContext):
    inputId = int(message.text)
    async with state.proxy() as data:
        data['input_id'] = int(message.text)
    if inputId in users:
        await message.answer(text='This user already in database', parse_mode='html')
        await state.finish()
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn = types.KeyboardButton(text='exit')
    markup.add(btn)
    await message.answer(text='Input username', reply_markup=markup, parse_mode='html')
    await Form.input_username.set()

@dp.message_handler(lambda message: message.text[0] != '@', state=Form.input_username)
async def input_username_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    return await message.reply("Username should be with @.\nInput username again (with @)")

@dp.message_handler(lambda message: message.text[0] == '@', state=Form.input_username)
async def input_username_successful(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['input_username'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
    btn = types.KeyboardButton(text='back')
    markup.add(btn)
    await message.answer(text='Input first_name', reply_markup=markup, parse_mode='html')
    await Form.input_firstname.set()

@dp.message_handler(lambda message: message.text[0] == '@', state=Form.input_firstname)
async def input_firstname_invalid(message: types.Message):
    return await message.reply("Firstname shouldn't be with @.\nInput firstname again (without @)")

@dp.message_handler(lambda message: message.text[0] != '@', state=Form.input_firstname)
async def input_firstname_successful(message: types.Message, state: FSMContext):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    else:
        async with state.proxy() as data:
            data['input_firstname'] = message.text
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
        btn1 = types.KeyboardButton(text='1week')
        btn2 = types.KeyboardButton(text='1month')
        btn3 = types.KeyboardButton(text='6month')
        btn4 = types.KeyboardButton(text='back')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        await message.answer(text='Input duration of subscription', reply_markup=markup, parse_mode='html')
        await Form.input_duration.set()

@dp.message_handler(lambda message: str(message.text).strip().lower() not in ['1week', '1month', '6month'], state=Form.input_duration)
async def input_duration_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    else:
        return await message.reply("Duration should be equal to example.\nExample '1week', '1month', '6month'")

@dp.message_handler(lambda message: str(message.text).strip().lower() in ['1week', '1month', '6month'], state=Form.input_duration)
async def input_duration_successful(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['input_duration'] = str(message.text).strip().lower()
    inputId = data['input_id']
    inputDuration = data['input_duration']
    inputUsername = data['input_username']
    inputFirstname = data['input_firstname']
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
    cur.execute("SELECT * FROM users WHERE id = '%d'" % (inputId))
    usersSQL = cur.fetchall()
    info = ''
    el = usersSQL[0]
    info += f'id = {el[0]}\nusername = {el[1]}\nfirst_name = {el[2]}\nstart_date = {el[3]}\nduration = {el[4]}\nend_of_date = {el[5]}\n'
    cur.close()
    conn.close()
    await message.answer(text=f'User added successfully\n{info}', parse_mode='html')
    await state.finish()



@dp.message_handler(commands=['delete'])
async def delete(message: types.Message):
    global admins
    if message.chat.id not in admins:
        await message.answer(text="You are not admin")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1, one_time_keyboard=True)
        btn = types.KeyboardButton(text='back')
        markup.add(btn)
        await message.answer(text='If you clicked here by accident and want to exit, write "exit".', reply_markup=markup)
        await message.answer(text='To delete a user, enter their id')
        await Form.delete_id.set()

@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.delete_id)
async def delete_id_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    return await message.reply("Id gotta be integer.\nInput id again (digits only)")

@dp.message_handler(lambda message: message.text.isdigit(), state=Form.delete_id)
async def delete_id_successful(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['delete_id'] = int(message.text)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    btn1 = types.KeyboardButton(text='yes')
    btn2 = types.KeyboardButton(text='no')
    markup.add(btn1, btn2)
    await message.answer(text='Are you sure to delete this user?', reply_markup=markup)
    await Form.delete_id_answer.set()

@dp.message_handler(lambda message: str(message.text).strip().lower() not in ['y', 'yes', 'da', 'да', '+', 'n', 'no', 'net', 'нет', '-'], state=Form.delete_id_answer)
async def delete_id_answer_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
        btn1 = types.KeyboardButton(text='yes')
        btn2 = types.KeyboardButton(text='no')
        markup.add(btn1, btn2)
        return await message.reply(text="Are you sure to delete this user?\nInput yes or no", reply_markup=markup)

@dp.message_handler(lambda message: str(message.text).strip().lower() in ['y', 'yes', 'da', 'да', '+', 'n', 'no', 'net', 'нет', '-'], state=Form.delete_id_answer)
async def delete_id_answer_successful(message: types.Message, state: FSMContext):
    text = message.text
    async with state.proxy() as data:
        data['delete_id_answer'] = text
        if text == 'y' or text == 'yes' or text == 'da' or text == 'да' or text =='+':
            if len(users) != 0:
                deleteId = data['delete_id']
                if deleteId in users:
                    conn = sqlite3.connect("users_bot.sql")
                    cur = conn.cursor()
                    cur.execute("DELETE FROM users WHERE id = '%d'" % (deleteId))
                    conn.commit()
                    users.remove(deleteId)
                    cur.close()
                    conn.close()
                    await message.answer(text=f"User with id = {deleteId} deleted.")
                    await state.finish()
                else:
                    await message.answer(text=f"User with id = {deleteId} not found.")
                    await state.finish()
                    return
            else:
                await message.answer(text=f"Database is empty.")
                await state.finish()
                return
        elif text == 'n' or text == 'no' or text == 'net' or text == 'нет' or text == '-':
            await message.answer(text="Nobody deleted.")
            await state.finish()
            return



@dp.message_handler(commands=['update'])
async def update(message: types.Message):
    global admins
    if message.chat.id not in admins:
        await message.answer(text="You are not admin")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1, one_time_keyboard=True)
        btn = types.KeyboardButton(text='exit')
        markup.add(btn)
        await message.answer(text='If you clicked here by accident and want to exit, push "exit".', reply_markup=markup)
        await message.answer(text='Enter the user id of the user whose data you want to update')
        await Form.update_id.set()

@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.update_id)
async def update_id_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    return await message.reply("Id gotta be integer.\nInput id again (digits only)")

@dp.message_handler(lambda message: message.text.isdigit(), state=Form.update_id)
async def update_id_successful(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['update_id'] = int(message.text)
    updateId = state.proxy()['update_id']
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
            await message.answer(message.chat.id, f"{info}", parse_mode='html')
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
            btn1 = types.KeyboardButton(text='username')
            btn2 = types.KeyboardButton(text='first_name')
            btn3 = types.KeyboardButton(text='duration')
            btn = types.KeyboardButton(text='exit')
            markup.row(btn1, btn2)
            markup.row(btn3, btn)
            await message.answer(text='What would you like to change?', reply_markup=markup)
            await Form.field_change.set()
        else:
            await message.answer(text=f'User with id = {updateId} not found.')
            return
    else:
        await message.answer(text='Database is empty.')
        return

@dp.message_handler(lambda message: str(message.text).strip().lower() not in ['username', 'first_name', 'duration'], state=Form.field_change)
async def field_change_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn1 = types.KeyboardButton(text='username')
        btn2 = types.KeyboardButton(text='first_name')
        btn3 = types.KeyboardButton(text='duration')
        btn = types.KeyboardButton(text='exit')
        markup.row(btn1, btn2)
        markup.row(btn3, btn)
        return await message.reply(text="You input incorrect data\nInput name of field again", reply_markup=markup)

@dp.message_handler(lambda message: str(message.text).strip().lower() in ['username', 'first_name', 'duration'], state=Form.field_change)
async def field_change_successful(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['field_change'] = str(message.text).strip().lower()
    field = state.proxy()['field_change']
    if field == 'username':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn = types.KeyboardButton(text='exit')
        markup.add(btn)
        await message.answer(text="Enter a new username with @", reply_markup=markup)
        await Form.update_username.set()
    elif field == 'first_name':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn = types.KeyboardButton(text='exit')
        markup.add(btn)
        await message.answer(text="Enter a new first_name.", reply_markup=markup)
        await Form.update_firstname.set()
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1)
        btn1 = types.KeyboardButton(text='1week')
        btn2 = types.KeyboardButton(text='1month')
        btn3 = types.KeyboardButton(text='6month')
        btn4 = types.KeyboardButton(text='exit')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        await message.answer(text="Enter a new duration.", reply_markup=markup)
        await Form.update_duration.set()

@dp.message_handler(lambda message: message.text[0] != '@', state=Form.update_username)
async def update_username_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    return await message.reply("Username should be with @.\nInput username again (with @)")

@dp.message_handler(lambda message: message.text[0] == '@', state=Form.update_username)
async def update_username_successful(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['update_username'] = message.text
    updateUsername = state.proxy()['update_username']
    updateId = state.proxy()['update_id']
    conn = sqlite3.connect("users_bot.sql")
    cur = conn.cursor()
    cur.execute("UPDATE users SET username = '%s' WHERE id = '%d'" % (updateUsername, updateId))
    conn.commit()
    cur.close()
    conn.close()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    btn1 = types.KeyboardButton(text='yes')
    btn2 = types.KeyboardButton(text='no')
    markup.add(btn1, btn2)
    await message.answer(text="Anything else you'd like to change?", reply_markup=markup)
    await Form.update_answer.set()

@dp.message_handler(lambda message: message.text[0] == '@', state=Form.update_firstname)
async def update_firstname_invalid(message: types.Message):
    return await message.reply("Firstname shouldn't be with @.\nInput firstname again (without @)")

@dp.message_handler(lambda message: message.text[0] != '@', state=Form.update_firstname)
async def update_firstname_successful(message: types.Message, state: FSMContext):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    else:
        async with state.proxy() as data:
            data['update_firstname'] = message.text
        updateId = state.proxy()['update_id']
        updateFirstname = state.proxy()['update_firstname']
        conn = sqlite3.connect("users_bot.sql")
        cur = conn.cursor()
        cur.execute("UPDATE users SET first_name = '%s' WHERE id = '%d'" % (updateFirstname, updateId))
        conn.commit()
        cur.close()
        conn.close()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
        btn1 = types.KeyboardButton(text='yes')
        btn2 = types.KeyboardButton(text='no')
        markup.add(btn1, btn2)
        await message.answer(text="Anything else you'd like to change?", reply_markup=markup)
        await Form.update_answer.set()

@dp.message_handler(lambda message: str(message.text).strip().lower() not in ['1week', '1month', '6month'], state=Form.update_duration)
async def update_duration_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    else:
        return await message.reply("Duration should be equal to example.\nExample '1week', '1month', '6month'")

@dp.message_handler(lambda message: str(message.text).strip().lower() in ['1week', '1month', '6month'], state=Form.update_duration)
async def update_duration_successful(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['update_duration'] = str(message.text).strip().lower()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    btn1 = types.KeyboardButton(text='yes')
    btn2 = types.KeyboardButton(text='no')
    markup.add(btn1, btn2)
    await message.answer(text="Do you want to change the start_date?")
    await Form.update_start_date.set()

@dp.message_handler(lambda message: str(message.text).strip().lower() not in ['y', 'yes', 'da', 'да', '+', 'n', 'no', 'net', 'нет', '-'], state=Form.update_start_date)
async def update_start_date_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
        btn1 = types.KeyboardButton(text='yes')
        btn2 = types.KeyboardButton(text='no')
        markup.add(btn1, btn2)
        return await message.reply(text="Are you want to change start date?\nInput yes or no", reply_markup=markup)

@dp.message_handler(lambda message: str(message.text).strip().lower() in ['y', 'yes', 'da', 'да', '+', 'n', 'no', 'net', 'нет', '-'], state=Form.update_start_date)
async def update_start_date_successful(message: types.Message, state: FSMContext):
    text = str(message.text).strip().lower()
    updateId = state.proxy()['update_id']
    updateDuration = state.proxy()['update_duration']
    if text == 'y' or text == 'yes' or text == 'da' or text == 'да' or text =='+':
        async with state.proxy() as data:
            data['update_start_date'] = datetime.now
        updateStartDate = state.proxy()['update_start_date']
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
        async with state.proxy() as data:
            data['update_end_date'] = updateEndOfDate
    elif text == 'n' or text == 'no' or text == 'net' or text == 'нет' or text == '-':
        updateId = state.proxy()['update_id']
        conn = sqlite3.connect("users_bot.sql")
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = '%d'" % (updateId))
        usersSQL = cur.fetchall()
        updateEl = usersSQL[0]
        cur.close()
        conn.close()
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
        async with state.proxy() as data:
            data['update_end_date'] = updateEndOfDate
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    btn1 = types.KeyboardButton(text='yes')
    btn2 = types.KeyboardButton(text='no')
    markup.add(btn1, btn2)
    await message.answer(text="Anything else you'd like to change?", reply_markup=markup)
    await Form.update_answer.set()

@dp.message_handler(lambda message: str(message.text).strip().lower() not in ['y', 'yes', 'da', 'да', '+', 'n', 'no', 'net', 'нет', '-'], state=Form.update_answer)
async def update_answer_invalid(message: types.Message):
    text = str(message.text).strip().lower()
    if text == 'exit':
        await message.answer(text="You've successfully exited")
        return
    else:
        return await message.reply("Write yes or no.")

@dp.message_handler(lambda message: str(message.text).strip().lower() in ['y', 'yes', 'da', 'да', '+', 'n', 'no', 'net', 'нет', '-'], state=Form.update_answer)
async def update_answer_successful(message: types.Message, state: FSMContext):
    text = str(message.text).strip().lower()
    async with state.proxy() as data:
        data['update_answer'] = str(message.text).strip().lower()
    if text == 'y' or text == 'yes' or text == 'da' or text == 'да' or text == '+':
        await message.answer(text="What would you like to change?")
        await Form.field_change.set()
    else:
        updateId = state.proxy()['update_id']
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
        await message.answer(text=f'User is updated successfully\nNew info about him:{info}\n')
    await state.finish()



@dp.message_handler(content_types=['text'])
async def getTextMessages(message: types.Message):
    global users, admins
    id = int(message.message_id)
    text = str(message.text).strip().lower()
    if text == "plans" or text == "plan":
        markup2 = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 1, one_time_keyboard=True)
        markup1 = types.InlineKeyboardMarkup()
        btnWeek = types.InlineKeyboardButton(text='1 week', callback_data='1week')
        btnMonth = types.InlineKeyboardButton(text='1 month', callback_data='1month')
        btn6Month = types.InlineKeyboardButton(text='6 month', callback_data='6month')
        markup1.add(btnWeek).add(btnMonth).add(btn6Month)
        btnSub = types.KeyboardButton(text='/subscription')
        markup2.add(btnSub)
        mess1 = f'There are 3 subscription plans available in this bot.\n1 week - 25 USDT\n1 month - 50 USDT\n6 months - 200 USDT'
        mess2 = f'If for some reason you are unable to pay your subscription via Wallet click on /subscription'
        await message.answer(text=mess1, reply_markup=markup1)
        await message.answer(text=mess2, reply_markup=markup2)
    elif text == "subscription": #поменять работу
        mess1 = 'If you have trouble paying via Wallet, you can send the subscription price in USDT (TRC20) currency to this address.\n`TAVvvzzS1357spwmaC9sLFVmwtKfJiddkN`\nOr use this qr-code:'
        mess2 = 'To confirm the payment you need a <u><b>screenshot</b></u> of the transfer and the <u><b>USDT address</b></u> from where the transfer was made.\nAfter successful payment, click on the button below.'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
        btn = types.KeyboardButton(text='/payment_confirmation')
        markup.add(btn)
        await message.answer(text=mess1, parse_mode='Markdown')
        await message.answer_photo(photo=qr)
        await message.answer(text=mess2, reply_markup=markup, parse_mode='html')
    elif text == "help":
        mess = '/start - main information about this bot.\n/show_chains - command to show the chains\n/plans - subscription options for this bot.\n/subscription - command for those who have problems with subscription.\n/problem - command for those who have any problems with the bot.\n/admin - list of admin commands.'
        await message.reply(mess)
    elif text == "show users" or text == "show user":
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
        await message.answer(text=info)
    elif text == "show chains" or text == "show chain" or text == "chain" or text == "chains":
        id = message.chat.id
        if id not in users and id not in admins:
            await message.answer(text="Sorry you didn't subscribe")
        else:
            markup = types.InlineKeyboardMarkup()
            btn = types.InlineKeyboardButton(text='reload chains', callback_data='reload_chains')
            markup.add(btn)
            Response = ""
            with open('Links.txt', 'r') as links:
                for line in links:
                    Response += line + '\n'
                mess = Response
                await message.answer(text=mess, reply_markup=markup, parse_mode='html')
                await bot.delete_message(id, message.message_id - 1)
                await bot.delete_message(id, message.message_id)



if __name__ == '__main__':
    from aiogram import executor
    dp.middleware.setup(AlbumMiddleware())
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)