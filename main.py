import telebot
from telebot import types
import sqlite3

import config
from config import bot_token, api_key_news, category_list
import requests

bot = telebot.TeleBot(bot_token)
news = []

def bd_users(user_id): # проверяем id, если нет добовляем
	us = sqlite3.connect('database.db', check_same_thread=False)
	cursor = us.cursor()
	answer = cursor.execute("""select id from users where id=?""", (user_id,)).fetchone()
	us.close()
	return answer

def bd_new_user(user_id):
	us = sqlite3.connect('database.db', check_same_thread=False)
	cursor = us.cursor()
	cursor.execute('INSERT INTO users(id) VALUES(?)', (user_id,))
	us.commit()
	us.close()

def bd_watch(user_id): # проверяем есть ли подписки у пользователя
	us = sqlite3.connect('database.db', check_same_thread=False)
	cur = us.cursor()
	res = cur.execute('''select name from categories
					INNER JOIN subscribes ON categories.id == subscribes.id_category
					INNER JOIN users ON users.id == subscribes.id_user
					where users.id=?''', (user_id,)).fetchall()
	us.close()
	return res

def bd_subscribe(): # список имеющихся категорий в базе
	us = sqlite3.connect('database.db', check_same_thread=False)
	cursor = us.cursor()
	res = cursor.execute('SELECT name FROM categories').fetchall()
	us.close()
	return res

def bd_subscribe_category(user_id, cat): #одписка пользователя на катерогию
	us = sqlite3.connect('database.db', check_same_thread=False)
	cursor = us.cursor()
	cursor.execute('''INSERT INTO subscribes(id_user, id_category) 
								VALUES (
								(?),
								(SELECT id FROM categories WHERE name=?)
								)''', (user_id, cat))
	us.commit()
	us.close()

def bd_new_category(user_id, cat):
	us = sqlite3.connect('database.db', check_same_thread=False)
	cursor = us.cursor()
	res = cursor.execute('''SELECT * From subscribes 
					INNER JOIN users ON users.id=id_user 
					INNER JOIN categories ON categories.id=id_category 
					WHERE users.id=? AND categories.name=?''', (user_id, cat)).fetchone()
	us.close()
	return res

def bd_del_category(user_id, cat):
	us = sqlite3.connect('database.db', check_same_thread=False)
	cursor = us.cursor()
	cursor.execute('''DELETE from subscribes where id_user=? and id_category=
	(SELECT id FROM categories WHERE name=?)''', (user_id, cat))
	us.commit()
	us.close()
	
try:
	connect = sqlite3.connect('database.db', check_same_thread=False)
	cursor = connect.cursor()
	cursor.execute("""CREATE TABLE IF NOT EXISTS "users" (
		"id"	INTEGER NOT NULL,
		PRIMARY KEY("id" AUTOINCREMENT)
	);""")
	cursor.execute("""CREATE TABLE IF NOT EXISTS "categories" (
		"id"	INTEGER NOT NULL,
		"name"	TEXT NOT NULL,
		PRIMARY KEY("id" AUTOINCREMENT)
	);""")
	cursor.execute("""CREATE TABLE IF NOT EXISTS "subscribes" (
		"id_user"	INTEGER NOT NULL,
		"id_category"	INTEGER NOT NULL
	);""")
	connect.commit()

	cat_list=cursor.execute("SELECT name FROM categories").fetchall()
	print(cat_list)
	if len(cat_list) == 0:
		for item in category_list:
			cursor.execute("INSERT INTO categories(name) VALUES(?)",(item,))
			connect.commit()
except:
	print('Error')
finally:
	connect.close()

def converList(news):
	str = ''
	for i in news:
		str += i+"\n"
	return str

@bot.message_handler(commands=['start'])
def send_welcome(message):
	user_id = int(message.from_user.id)
	print(message.from_user.id)
	try:
		if len(bd_users(user_id)) == 0:
			bd_new_user(user_id)
			bot.send_message(message.from_user.id, "Здравствуйте")
		else:
			bot.send_message(message.from_user.id, "Приятно видеть вас снова")
	except sqlite3.Error as error:
		bot.send_message(message.from_user.id, "error")

@bot.message_handler(commands=['help'])
def send_welcome(message):
	bot.reply_to(message, "/new-новости")

@bot.message_handler(commands=['categoty'])
def send_welcome(message):
	markup = types.InlineKeyboardMarkup(row_width=1)
	subscribe = types.InlineKeyboardButton("Подписаться на категорию новостей", callback_data='subscribe')
	unsubscribe = types.InlineKeyboardButton("Отписаться от категории новостей", callback_data='unsubscribe')
	watch = types.InlineKeyboardButton("Посмотреть имеющиеся подписки на категориии новостей", callback_data='watch')
	news = types.InlineKeyboardButton("Хочу почитать новости", callback_data='news')
	markup.add(subscribe,unsubscribe,watch, news)
	bot.send_message(message.chat.id, 'Выбире что хотите сделать?', reply_markup=markup)

@bot.message_handler(commands=['new'])
def send_welcome(message):
	categoty = 'health'
	a = requests.get(f'https://newsapi.org/v2/top-headlines?apiKey={api_key_news}&category={categoty}&pageSize=3')
	for i in a.json()['articles']:
		news.append([i['title'], i['publishedAt'], i['url']])
	answer = ""
	for line in news:
		answer+=converList(line)+"---------------\n"
	bot.send_message(message.chat.id, answer)

@bot.callback_query_handler(func=lambda call:True)
def callback(call):
	# print(call.message)
	# print(type(call.message),call.data, type(call.data))
	if call.message:
		if call.data == "watch":
				user_id=int(call.from_user.id)
				# print(user_id,"111")
				cats = bd_watch(user_id)
				# print(cats)
				if len(cats) != 0:
					str = ""
					for i in cats:
						str += f'{i[0]}, '
					bot.send_message(call.message.chat.id, f"Вы подписаны на {str}")
				else:
					bot.send_message(call.message.chat.id, "У вас пока что нет подписок")
		if call.data == "subscribe":
				cate = bd_subscribe()
				markup = types.InlineKeyboardMarkup(row_width=1)
				for i in cate:
					markup.add(types.InlineKeyboardButton(text=f'{i[0]}', callback_data=f'{i[0]}'))
				bot.send_message(call.message.chat.id, "Выберите категорию на которую хотите подписаться",reply_markup=markup)
		if  call.data in config.category_list:
				user_id = int(call.from_user.id)
				cat = call.data
				res = bd_new_category(user_id, cat)
				print(cat, type(cat))
				print(res,user_id)
				if res is not None:
					bot.send_message(call.message.chat.id, "Вы уже подписаны на эту категорию")
				else:
					bd_subscribe_category(user_id, cat)
					bot.send_message(call.message.chat.id, "Вы успешно подписались")

		if call.data == "unsubscribe":
			user_id = int(call.from_user.id)
			cats = bd_watch(user_id)
			markup = types.InlineKeyboardMarkup(row_width=1)
			for i in cats:
				markup.add(types.InlineKeyboardButton(text=f'unsub_{i[0]}', callback_data=f'unsub_{i[0]}'))
			bot.send_message(call.message.chat.id, "Выберите категорию от которой хотите отподписаться",
							 reply_markup=markup)
			# for i in cats:
			# 	print(i)
		if call.data.startswith('unsub') and call.data[6:] in config.category_list:
			user_id = int(call.from_user.id)
			cat=call.data[6:]
			print(cat)
			bd_del_category(user_id, cat)
			bot.send_message(call.message.chat.id, "Вы успешно отписались")
		if call.data == "news":
			user_id = int(call.from_user.id)
			cats = bd_watch(user_id)
			markup = types.InlineKeyboardMarkup(row_width=1)
			for i in cats:
				markup.add(types.InlineKeyboardButton(text=f'new_{i[0]}', callback_data=f'new_{i[0]}'))
			bot.send_message(call.message.chat.id, "Выберите категорию новостей, которую хоите почитать",
							 reply_markup=markup)
		if call.data.startswith('new') and call.data[4:] in config.category_list:
			cat = call.data[4:]
			print(cat)
			a = requests.get(
				f'https://newsapi.org/v2/top-headlines?apiKey={api_key_news}&category={cat}&pageSize=3')
			for i in a.json()['articles']:
				news.append([i['title'], i['publishedAt'], i['url']])
			answer = ""
			for line in news:
				answer += converList(line) + "---------------\n"
			bot.send_message(call.message.chat.id, answer)

bot.infinity_polling()