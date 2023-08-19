import telebot
import subprocess
import datetime
import mysql.connector
import time
import schedule
from datetime import datetime, timedelta
import io
import os
import threading
from dotenv import load_dotenv
import functools
from telebot import types
from telegram.constants import ParseMode

# Load environment variables from .env file
load_dotenv()

# Get environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
CHANNEL_ID = os.getenv("CHANNEL_ID")
AUTHORIZED_CHAT_IDS = os.getenv("AUTHORIZED_CHAT_IDS", "").split(",")


# Set up the Telegram bot
bot = telebot.TeleBot(BOT_TOKEN)


# Set up the MySQL database connection
db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)
cursor = db.cursor()


# Set up the Start keyboard
start_button = types.KeyboardButton('🏁 START')
start_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
start_keyboard.add(start_button)

# Set up the Menu keyboard
button1 = types.KeyboardButton('🙋 Add User') 
button2 = types.KeyboardButton('😔 Delete User')
button3 = types.KeyboardButton('🔒 Lock User')
button4 = types.KeyboardButton('🔐 Lock Expired')  
button5 = types.KeyboardButton('🔓 Unlock User')
button6 = types.KeyboardButton('⌛ Update Expiration')
button7 = types.KeyboardButton('⚙️ Update User')
button8 = types.KeyboardButton('🔄 Renew User')
button9 = types.KeyboardButton('🔍 Search User')
button10 = types.KeyboardButton('🧑 Online Users')
button11 = types.KeyboardButton('📋 All Users')  
button12 = types.KeyboardButton('🟢 Active Users')
button13 = types.KeyboardButton('🔴 Inactive Users')
button14 = types.KeyboardButton('📦 DB Backup')
button15 = types.KeyboardButton('📄 Ocpasswd Backup')
button16 = types.KeyboardButton('⚡ Restart Bot')
button17 = types.KeyboardButton('❓ Help')
button18 = types.KeyboardButton('👋 Exit')
menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
menu_keyboard.add(button1,button2,button3,button4,button5,button6,button7,button8,button9,
         button10,button11,button12,button13,button14,button15,button16,button17,
         button18)

# Set up the Cancel keyboard
cancel_button = types.KeyboardButton('🚫 Cancel')
cancel_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
cancel_keyboard.add(cancel_button)


# Command: /start
@bot.message_handler(commands=['start'])
def start(message):

  bot.send_message(
    message.chat.id,
    "Welcome to AliNet Bot!😉 Touch Start to get started.",
    reply_markup=start_keyboard
  )

@bot.message_handler(func=lambda message: message.text == "🏁 START")  
def show_menu(message):
  bot.send_message(message.chat.id, "Choose an Option:",  
                    reply_markup=menu_keyboard)


# Decorator function to check user authorization
def authorized_only(func):
    @functools.wraps(func)
    def wrapper(message, *args, **kwargs):
        if str(message.chat.id) in AUTHORIZED_CHAT_IDS:
            return func(message, *args, **kwargs)
        else:
            bot.send_message(message.chat.id, "⛔ Access denied ⛔")
    return wrapper


# Command: /adduser
@bot.message_handler(func=lambda message: message.text == "🙋 Add User")
@authorized_only
def add_user(message):
    msg = bot.send_message(message.chat.id, "Enter the Username:",  
                         reply_markup=cancel_keyboard)
    bot.register_next_step_handler(msg, process_username_step)
    
def process_username_step(message):
    if message.text == "🚫 Cancel":  
     bot.send_message(message.chat.id, "🚫 Add User Operation Canceled!", reply_markup=menu_keyboard)
     return

    username = message.text.lower()

    # Check if the username already exists in the database
    query = "SELECT COUNT(*) FROM users WHERE username = %s"
    values = (username,)
    cursor.execute(query, values)
    result = cursor.fetchone()

    if result[0] > 0:
        bot.send_message(message.chat.id, "🚫 User already exists. Choose another username.", reply_markup=menu_keyboard)
        return

    # Continue with the process if the username is unique
    msg = bot.send_message(message.chat.id, "Enter the Password:")
    bot.register_next_step_handler(msg, process_password_step, username)

def process_password_step(message, username):
    if message.text == "🚫 Cancel":  
     bot.send_message(message.chat.id, "🚫 Add User Operation Canceled!", reply_markup=menu_keyboard)
     return

    password = message.text

    msg = bot.send_message(message.chat.id, "Enter the number of days or a specific date (YYYY-MM-DD format):")
    bot.register_next_step_handler(msg, process_days_or_date_step, username, password)

def process_days_or_date_step(message, username, password):
    if message.text == "🚫 Cancel":  
     bot.send_message(message.chat.id, "🚫 Add User Operation Canceled!", reply_markup=menu_keyboard)
     return

    input_text = message.text.strip()

    try:
        days = int(input_text)
        if days < 0:
            bot.send_message(message.chat.id, "🚫 Number of days cannot be negative. Please enter a non-negative value.")
            return

        expire_datetime = datetime.now() + timedelta(days=days)
    except ValueError:
        try:
            expire_datetime = datetime.strptime(input_text, '%Y-%m-%d')
            if expire_datetime < datetime.now():
                bot.send_message(message.chat.id, "🚫 Entered date is in the past. Please enter a future date.")
                return
        except ValueError:
            bot.send_message(message.chat.id, "🚫 Invalid input. Please enter either a number of days or a date in YYYY-MM-DD format.")
            return

    start_date = datetime.now().strftime('%Y-%m-%d')
    expire_date = expire_datetime.strftime('%Y-%m-%d')

    # Execute the ocpasswd command with the entered username and password
    command = ['sudo', 'ocpasswd', '-c', '/etc/ocserv/ocpasswd', username]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    process.communicate(input=password.encode())  # Pass the password as input to the process

    # Insert user data into the database
    query = "INSERT INTO users (username, password, start_date, expire_date, status) VALUES (%s, %s, %s, %s, %s)"
    values = (username, password, start_date, expire_date, 'active')
    cursor.execute(query, values)
    db.commit()

    bold_username = f"<b>\"{username}\"</b>"
    bold_password = f"<b>\"{password}\"</b>"  
    bold_expire = f"<b>\"{expire_date}\"</b>"
    message = bot.send_message(message.chat.id,
                            f"✅ User {bold_username} Added Successfully!\n"
                            f"Password: {bold_password}\n"
                            f"Expire Date: {bold_expire}",
                            parse_mode=ParseMode.HTML,
                            reply_markup=menu_keyboard)


# Command: /deluser
@bot.message_handler(func=lambda message: message.text == "😔 Delete User")
@authorized_only
def del_user(message):
    msg = bot.send_message(message.chat.id, "Enter the Username:",  
                         reply_markup=cancel_keyboard)
    bot.register_next_step_handler(msg, process_deluser_step)
    
def process_deluser_step(message):
    if message.text == "🚫 Cancel":  
     bot.send_message(message.chat.id, "🚫 User Deletion Operation Canceled!", reply_markup=menu_keyboard)
     return

    username = message.text.lower()

    # Check if the user exists in the database
    query_check = "SELECT COUNT(*) FROM users WHERE username = %s"
    values_check = (username,)
    cursor.execute(query_check, values_check)
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        bot.send_message(message.chat.id, "🚫 User does not exist.", reply_markup=menu_keyboard)
    else:
        # Remove the user from ocserv
        subprocess.run(['sudo', 'ocpasswd', '-d', username])

        # Remove the user from the database
        query_delete = "DELETE FROM users WHERE username = %s"
        values_delete = (username,)
        cursor.execute(query_delete, values_delete)
        db.commit()

        bold_username = f"<b>\"{username}\"</b>"
        bot.send_message(message.chat.id, 
                        f"✅ User {bold_username} Deleted Successfully!",
                        parse_mode=ParseMode.HTML,
                        reply_markup=menu_keyboard)


# Command: /lockuser
@bot.message_handler(func=lambda message: message.text == "🔒 Lock User")
@authorized_only
def lock_user(message):
    msg = bot.send_message(message.chat.id, "Enter the Username:",  
                         reply_markup=cancel_keyboard)
    bot.register_next_step_handler(msg, process_lockuser_step)

def process_lockuser_step(message):
    if message.text == "🚫 Cancel":  
     bot.send_message(message.chat.id, "🚫 User Locking Operation Canceled!", reply_markup=menu_keyboard)
     return

    username = message.text.lower()

    # Check if the user is already locked (status = 'deactive') in the database
    query_check = "SELECT status FROM users WHERE username = %s"
    values_check = (username,)
    cursor.execute(query_check, values_check)
    user_status = cursor.fetchone()

    if user_status and user_status[0] == 'deactive':
        bot.send_message(message.chat.id, "User is already Locked.")
    else:
        # Disconnect the user from ocserv
        subprocess.run(['sudo', 'occtl', 'disconnect', 'user', username])

        # Lock the user in ocserv
        subprocess.run(['sudo', 'ocpasswd', '-l', username])

        # Update the user status in the database
        query_update = "UPDATE users SET status = 'deactive' WHERE username = %s"
        values_update = (username,)
        cursor.execute(query_update, values_update)
        db.commit()

        bold_username = f"<b>\"{username}\"</b>"
        bot.send_message(message.chat.id,
                        f"🔒 User {bold_username} Locked Successfully!",
                        parse_mode=ParseMode.HTML,
                        reply_markup=menu_keyboard)


# Command: /unlockuser
@bot.message_handler(func=lambda message: message.text == "🔓 Unlock User")
@authorized_only
def unlock_user(message):
    msg = bot.send_message(message.chat.id, "Enter the Username:",  
                         reply_markup=cancel_keyboard)
    bot.register_next_step_handler(msg, process_unlockuser_step)

def process_unlockuser_step(message):
    if message.text == "🚫 Cancel":  
     bot.send_message(message.chat.id, "🚫 User UnLocking Operation Canceled!", reply_markup=menu_keyboard)
     return

    username = message.text.lower()

    # Check if the user is already unlocked (status = 'active') in the database
    query_check = "SELECT status FROM users WHERE username = %s"
    values_check = (username,)
    cursor.execute(query_check, values_check)
    user_status = cursor.fetchone()

    if user_status and user_status[0] == 'active':
        bot.send_message(message.chat.id, "User is already UnLocked.")
    else:
        # Unlock the user in ocserv
        subprocess.run(['sudo', 'ocpasswd', '-u', username])

        # Update the user status in the database
        query_update = "UPDATE users SET status = 'active' WHERE username = %s"
        values_update = (username,)
        cursor.execute(query_update, values_update)
        db.commit()

        bold_username = f"<b>\"{username}\"</b>"
        bot.send_message(message.chat.id,
                        f"🔓 User {bold_username} UnLocked Successfully!",
                        parse_mode=ParseMode.HTML,
                        reply_markup=menu_keyboard) 


# Command: /onlineusers
@bot.message_handler(func=lambda message: message.text == "🧑 Online Users")
@authorized_only
def online_users(message):
    output = subprocess.check_output(['sudo', 'occtl', 'show', 'users']).decode('utf-8')
    
    # Parse the output and extract user and since information
    lines = output.strip().split('\n')
    headers = lines[0].split()
    data = [line.split() for line in lines[1:]]
    
    # Find the indices of the 'user' and 'since' columns
    user_index = headers.index('user')
    since_index = headers.index('since')
    
    num_online_users = len(data)  # Get the total number of online users
    
    max_message_length = 4096  # Maximum message length supported by Telegram
    chunk = f"Online Users ({num_online_users})🧑\n"
    chunk += "- - - - - - - - - - - - - - - - -\n"
    
    for index, row in enumerate(data, start=1):
        user = row[user_index]
        since = row[since_index]
        
        user_info = (
            f"{index}- User: {user}, Since: {since}\n"
            "- - - - - - - - - - - - - - - - -\n"
        )
        
        # Check if adding the user_info to the current chunk exceeds the message length limit
        if len(chunk) + len(user_info) > max_message_length:
            # Send the current chunk as a message
            bot.send_message(message.chat.id, chunk)
            # Reset the chunk
            chunk = ""
        
        # Add the user_info to the current chunk
        chunk += user_info
    
    # Send the remaining chunk as a message (if not empty)
    if chunk:
        bot.send_message(message.chat.id, chunk)


# Command: /allusers
@bot.message_handler(commands=['allusers'])
@authorized_only
def all_users(message):
    query = "SELECT username, password, status, expire_date FROM users"
    cursor.execute(query)
    users = cursor.fetchall()

    num_users = len(users)  # Get the number of users

    response = f"All users ({num_users}):\n"
    response += "- - - - - - - - - - - - - - - - -\n"
    
    max_message_length = 4096  # Maximum message length supported by Telegram
    chunk = ""  # Initialize an empty chunk
    
    for index, user in enumerate(users, start=1):
        username = user[0]
        password = user[1]
        status = user[2]
        expire_date = user[3].strftime('%Y-%m-%d')

        remaining_days = max((datetime.strptime(expire_date, '%Y-%m-%d') - datetime.now()).days, 0)

        user_info = (
            f"{index}- Username: {username}\n"
            f"   Password: {password}\n"
            f"   Status: {status}\n"
            f"   Expiration Date: {expire_date}\n"
            f"   Remaining Days: {remaining_days}\n"
            "- - - - - - - - - - - - - - - - -\n"
        )
        
        # Check if adding the user_info to the current chunk exceeds the message length limit
        if len(chunk) + len(user_info) > max_message_length:
            # Send the current chunk as a message
            bot.send_message(message.chat.id, chunk)
            # Reset the chunk
            chunk = ""
        
        # Add the user_info to the current chunk
        chunk += user_info
    
    # Send the remaining chunk as a message (if not empty)
    if chunk:
        bot.send_message(message.chat.id, chunk)


# Command: /searchuser
@bot.message_handler(commands=['searchuser'])
@authorized_only
def search_user(message):
    msg = bot.send_message(message.chat.id, "Enter the username (type 'cancel' to abort):")
    bot.register_next_step_handler(msg, process_searchuser_step)

def process_searchuser_step(message):
    if message.text.lower() == "cancel":
        bot.send_message(message.chat.id, "Search user operation canceled.")
        return

    username = message.text

    # Get the user information from the database
    query = "SELECT * FROM users WHERE username = %s"
    values = (username,)
    cursor.execute(query, values)
    user = cursor.fetchone()

    if user:
        start_date = user[3]
        expire_date = user[4].strftime('%Y-%m-%d')

        remaining_days = max((datetime.strptime(expire_date, '%Y-%m-%d') - datetime.now()).days, 0)

        response = f"Username: {user[1]}\nPassword: {user[2]}\nStart Date: {start_date}\nExpire Date: {expire_date}\nStatus: {user[5]}\nRemaining Days: {remaining_days}"
    else:
        response = "User not found!"

    bot.send_message(message.chat.id, response)


# Command: /updateuser
@bot.message_handler(commands=['updateuser'])
@authorized_only
def update_user(message):
    msg = bot.send_message(message.chat.id, "Enter the username (type 'cancel' to abort):")
    bot.register_next_step_handler(msg, process_update_username_step)

def process_update_username_step(message):
    if message.text.lower() == "cancel":
        bot.send_message(message.chat.id, "Update user operation canceled.")
        return

    username = message.text.lower()

    # Check if the username exists in the database
    query = "SELECT COUNT(*) FROM users WHERE username = %s"
    values = (username,)
    cursor.execute(query, values)
    result = cursor.fetchone()

    if result[0] == 0:
        bot.send_message(message.chat.id, "User does not exist.")
        return

    # Continue with the process if the username exists
    msg = bot.send_message(message.chat.id, "Enter the new password:")
    bot.register_next_step_handler(msg, process_update_password_step, username)

def process_update_password_step(message, username):
    if message.text.lower() == "cancel":
        bot.send_message(message.chat.id, "Update user operation canceled.")
        return

    new_password = message.text

    msg = bot.send_message(message.chat.id, "Enter the number of days or a specific date (YYYY-MM-DD format) for connection:")
    bot.register_next_step_handler(msg, process_update_days_or_date_step, username, new_password)

def process_update_days_or_date_step(message, username, new_password):
    if message.text.lower() == "cancel":
        bot.send_message(message.chat.id, "Update user operation canceled.")
        return

    input_text = message.text.strip()

    try:
        days = int(input_text)
        if days < 0:
            bot.send_message(message.chat.id, "Number of days cannot be negative. Please enter a non-negative value.")
            return

        new_expire_datetime = datetime.now() + timedelta(days=days)
    except ValueError:
        try:
            new_expire_datetime = datetime.strptime(input_text, '%Y-%m-%d')
            if new_expire_datetime < datetime.now():
                bot.send_message(message.chat.id, "Entered date is in the past. Please enter a future date.")
                return
        except ValueError:
            bot.send_message(message.chat.id, "Invalid input. Please enter either a number of days or a date in YYYY-MM-DD format.")
            return

    new_expire_date = new_expire_datetime.strftime('%Y-%m-%d')

    # Update the user's password in ocserv
    command = ['sudo', 'ocpasswd', '-c', '/etc/ocserv/ocpasswd', username]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    process.communicate(input=new_password.encode())  # Pass the new password as input to the process

    # Update the user's information in the database
    query = "UPDATE users SET password = %s, expire_date = %s WHERE username = %s"
    values = (new_password, new_expire_date, username)
    cursor.execute(query, values)
    db.commit()

    bot.send_message(message.chat.id, "User information updated successfully!")


# Command: /updateexpiration
@bot.message_handler(commands=['updateexpiration'])
@authorized_only
def update_expiration_date(message):
    msg = bot.send_message(message.chat.id, "Enter the username (type 'cancel' to abort):")
    bot.register_next_step_handler(msg, process_update_username_step)

def process_update_username_step(message):
    if message.text.lower() == "cancel":
        bot.send_message(message.chat.id, "Update expiration date operation canceled.")
        return

    username = message.text.lower()

    # Check if the username exists in the database
    query = "SELECT COUNT(*) FROM users WHERE username = %s"
    values = (username,)
    cursor.execute(query, values)
    result = cursor.fetchone()

    if result[0] == 0:
        bot.send_message(message.chat.id, "User does not exist.")
        return

    # Continue with the process if the username exists
    msg = bot.send_message(message.chat.id, "Enter the number of days or a specific date (YYYY-MM-DD format):")
    bot.register_next_step_handler(msg, process_update_days_or_date_step, username)

def process_update_days_or_date_step(message, username):
    if message.text.lower() == "cancel":
        bot.send_message(message.chat.id, "Update expiration date operation canceled.")
        return

    input_text = message.text.strip()

    try:
        days = int(input_text)
        if days < 0:
            bot.send_message(message.chat.id, "Number of days cannot be negative. Please enter a non-negative value.")
            return

        new_expire_datetime = datetime.now() + timedelta(days=days)
    except ValueError:
        try:
            new_expire_datetime = datetime.strptime(input_text, '%Y-%m-%d')
            if new_expire_datetime < datetime.now():
                bot.send_message(message.chat.id, "Entered date is in the past. Please enter a future date.")
                return
        except ValueError:
            bot.send_message(message.chat.id, "Invalid input. Please enter either a number of days or a date in YYYY-MM-DD format.")
            return

    new_expire_date = new_expire_datetime.strftime('%Y-%m-%d')

    # Update the user's expiration date in the database
    query = "UPDATE users SET expire_date = %s WHERE username = %s"
    values = (new_expire_date, username)
    cursor.execute(query, values)
    db.commit()

    bot.send_message(message.chat.id, f"Expiration date for user {username} updated successfully to {new_expire_date}!")


# Command: /renewuser
@bot.message_handler(commands=['renewuser'])
@authorized_only
def renew_user(message):
    msg = bot.send_message(message.chat.id, "Enter the username (type 'cancel' to abort):")
    bot.register_next_step_handler(msg, process_renew_username_step)

def process_renew_username_step(message):
    if message.text.lower() == "cancel":
        bot.send_message(message.chat.id, "Renew user operation canceled.")
        return

    username = message.text.lower()

    # Check if the username exists in the database
    query = "SELECT COUNT(*) FROM users WHERE username = %s"
    values = (username,)
    cursor.execute(query, values)
    result = cursor.fetchone()

    if result[0] == 0:
        bot.send_message(message.chat.id, "User does not exist.")
        return

    msg = bot.send_message(message.chat.id, "Enter the number of days or a specific date (YYYY-MM-DD format) to extend the expiration date:")
    bot.register_next_step_handler(msg, process_renew_days_or_date_step, username)

def process_renew_days_or_date_step(message, username):
    if message.text.lower() == "cancel":
        bot.send_message(message.chat.id, "Renew user operation canceled.")
        return

    input_value = message.text.strip()

    if input_value.lstrip('-').isdigit():
        days = int(input_value)
        process_renew_days_step(message, username, days)
    else:
        process_renew_date_step(message, username, input_value)

def unlock_user(username):
    # Unlock the user in ocserv
    subprocess.run(['sudo', 'ocpasswd', '-u', username])

    # Update the user status in the database
    query = "UPDATE users SET status = 'active' WHERE username = %s"
    cursor.execute(query, (username,))
    db.commit()

def process_renew_days_step(message, username, days):
    if days <= 0:
        bot.send_message(message.chat.id, "Invalid input: Please enter a positive number of days.")
        return

    # Get the current expire date
    query = "SELECT expire_date FROM users WHERE username = %s"
    values = (username,)
    cursor.execute(query, values)
    current_expire_date = cursor.fetchone()[0]

    # Calculate the new expiration date based on the current expire date
    if current_expire_date <= datetime.now().date():
        new_expire_date = datetime.now().date() + timedelta(days=days)
    else:
        current_expire_date_str = current_expire_date.strftime('%Y-%m-%d')
        current_expire_datetime = datetime.strptime(current_expire_date_str, '%Y-%m-%d')
        new_expire_datetime = current_expire_datetime + timedelta(days=days)
        new_expire_date = new_expire_datetime.date()

    # Update the user's information in the database
    query = "UPDATE users SET expire_date = %s WHERE username = %s"
    values = (new_expire_date, username)
    cursor.execute(query, values)
    db.commit()

    # Unlock the user if necessary
    query = "SELECT status FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    user_status = cursor.fetchone()[0]

    if user_status == 'deactive':
        unlock_user(username)
        bot.send_message(message.chat.id, "User expiration date renewed and user unlocked successfully!")
    else:
        bot.send_message(message.chat.id, "User expiration date renewed successfully!")

def process_renew_date_step(message, username, date_str):
    try:
        new_expire_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if new_expire_date < datetime.now().date():
            bot.send_message(message.chat.id, "Invalid date: Please enter a future date or today's date.")
            return
    except ValueError:
        bot.send_message(message.chat.id, "Invalid date format. Please use YYYY-MM-DD format.")
        return

    # Update the user's information in the database
    query = "UPDATE users SET expire_date = %s WHERE username = %s"
    values = (new_expire_date, username)
    cursor.execute(query, values)
    db.commit()

    # Unlock the user if necessary
    query = "SELECT status FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    user_status = cursor.fetchone()[0]

    if user_status == 'deactive':
        unlock_user(username)
        bot.send_message(message.chat.id, "User expiration date renewed and user unlocked successfully!")
    else:
        bot.send_message(message.chat.id, "User expiration date renewed successfully!")


# Command: /activeusers
@bot.message_handler(commands=['activeusers'])
@authorized_only
def active_users(message):
    query = "SELECT username, start_date, expire_date FROM users WHERE status = 'active'"
    cursor.execute(query)
    active_users_data = cursor.fetchall()

    if not active_users_data:
        bot.send_message(message.chat.id, "No active users found.")
        return

    number_of_active_users = len(active_users_data)
    response = f"Active Users({number_of_active_users}):\n"
    response += "- - - - - - - - - - - - - - - - -\n"
    
    max_message_length = 4096  # Maximum message length supported by Telegram
    chunk = ""  # Initialize an empty chunk
    
    for index, user in enumerate(active_users_data, start=1):
        username = user[0]
        start_date = user[1].strftime('%Y-%m-%d')
        expire_date = user[2].strftime('%Y-%m-%d')

        remaining_days = max((datetime.strptime(expire_date, '%Y-%m-%d') - datetime.now()).days, 0)

        user_info = (
            f"{index}- Username: {username}\n"
            f"   Start Date: {start_date}\n"
            f"   Expire Date: {expire_date}\n"
            f"   Remaining Days: {remaining_days}\n"
            "- - - - - - - - - - - - - - - - -\n"
        )
        
        # Check if adding the user_info to the current chunk exceeds the message length limit
        if len(chunk) + len(user_info) > max_message_length:
            # Send the current chunk as a message
            bot.send_message(message.chat.id, chunk)
            # Reset the chunk
            chunk = ""
        
        # Add the user_info to the current chunk
        chunk += user_info
    
    # Send the remaining chunk as a message (if not empty)
    if chunk:
        bot.send_message(message.chat.id, chunk)


# Command: /inactiveusers
@bot.message_handler(commands=['inactiveusers'])
@authorized_only
def inactive_users(message):
    query = "SELECT username, start_date, expire_date FROM users WHERE status = 'deactive'"
    cursor.execute(query)
    inactive_users_data = cursor.fetchall()

    if not inactive_users_data:
        bot.send_message(message.chat.id, "No inactive users found.")
        return

    number_of_inactive_users = len(inactive_users_data)
    response = f"Inactive Users({number_of_inactive_users}):\n"
    response += "- - - - - - - - - - - - - - - - -\n"
    
    max_message_length = 4096  # Maximum message length supported by Telegram
    chunk = ""  # Initialize an empty chunk
    
    for index, user in enumerate(inactive_users_data, start=1):
        username = user[0]
        start_date = user[1].strftime('%Y-%m-%d')
        expire_date = user[2].strftime('%Y-%m-%d')

        remaining_days = max((datetime.strptime(expire_date, '%Y-%m-%d') - datetime.now()).days, 0)

        user_info = (
            f"{index}- Username: {username}\n"
            f"   Start Date: {start_date}\n"
            f"   Expire Date: {expire_date}\n"
            f"   Remaining Days: {remaining_days}\n"
            "- - - - - - - - - - - - - - - - -\n"
        )
        
        # Check if adding the user_info to the current chunk exceeds the message length limit
        if len(chunk) + len(user_info) > max_message_length:
            # Send the current chunk as a message
            bot.send_message(message.chat.id, chunk)
            # Reset the chunk
            chunk = ""
        
        # Add the user_info to the current chunk
        chunk += user_info
    
    # Send the remaining chunk as a message (if not empty)
    if chunk:
        bot.send_message(message.chat.id, chunk)


# Command: /lockexpiredusers
@bot.message_handler(commands=['lockexpiredusers'])
@authorized_only
def lock_expired_users(message=None):
    if message:
        # This is the message handler version
        # Get the current date
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Get the expired users from the database
        query = "SELECT username FROM users WHERE expire_date <= %s AND status = 'active'"
        values = (current_date,)
        cursor.execute(query, values)
        expired_users = cursor.fetchall()

        # Check if there are expired users
        if len(expired_users) == 0:
            bot.send_message(message.chat.id, "There are no expired and active users.")
            return

        # Lock the expired users
        locked_users = []
        for user in expired_users:
            username = user[0]

            # Disconnect the user from ocserv
            subprocess.run(['sudo', 'occtl', 'disconnect', 'user', username])

            # Lock the user in ocserv
            subprocess.run(['sudo', 'ocpasswd', '-l', username])

            # Update the user status in the database
            query = "UPDATE users SET status = 'deactive' WHERE username = %s"
            values = (username,)
            cursor.execute(query, values)
            db.commit()

            # Add the locked user to the list
            locked_users.append(username)

        # Send a message to the bot indicating the locked users
        locked_users_message = '\n'.join(locked_users)
        bot.send_message(message.chat.id, f"Locked users:\n{locked_users_message}")

    else:
        # This is the scheduled task version

        chat_id = CHANNEL_ID
        # Get the current date
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Get the expired users from the database
        query = "SELECT username FROM users WHERE expire_date <= %s AND status = 'active'"
        values = (current_date,)
        cursor.execute(query, values)
        expired_users = cursor.fetchall()
                
        # Check if there are expired users
        if len(expired_users) == 0:
            bot.send_message(chat_id, "There are no expired and active users.")
            return

        # Lock the expired users
        locked_users = []
        for user in expired_users:
            username = user[0]

            # Disconnect the user from ocserv
            subprocess.run(['sudo', 'occtl', 'disconnect', 'user', username])

            # Lock the user in ocserv
            subprocess.run(['sudo', 'ocpasswd', '-l', username])

            # Update the user status in the database
            query = "UPDATE users SET status = 'deactive' WHERE username = %s"
            values = (username,)
            cursor.execute(query, values)
            db.commit()

            # Add the locked user to the list
            locked_users.append(username)

        # Send a message to the bot indicating the locked users
        locked_users_message = '\n'.join(locked_users)
        
        bot.send_message(chat_id, f"Scheduled lock expired users:\n{locked_users_message}")


# Command: /backupdb
@bot.message_handler(commands=['backupdb'])
@authorized_only
def backup_mysql_db(message=None):
    if message:
        # This is the message handler version
        chat_id = message.chat.id
        
        bot.send_message(chat_id, "Initiating database backup...")
        current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        backup_directory = '/bot/backup/'
        backup_file = os.path.join(backup_directory, f"backup_{current_datetime}.sql")

        if not os.path.exists(backup_directory):
            os.makedirs(backup_directory)

        working_directory = backup_directory

        with open(backup_file, 'wb') as f:
            process = subprocess.Popen(
                ['mysqldump', '-u', 'ali', '--password=8540', 'alidb'],
                stdout=f,
                cwd=working_directory
            )
            process.wait()

        with open(backup_file, 'rb') as f:
            file_content = f.read()

        with io.BytesIO(file_content) as document_io:
            document_io.name = backup_file
            bot.send_document(chat_id=chat_id, document=document_io)

        bot.send_message(chat_id, "Database backup completed and sent.")
    else:
        # This is the scheduled task version
        chat_id = CHANNEL_ID
        
        bot.send_message(chat_id, "Initiating scheduled database backup...")
        current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        backup_directory = '/bot/backup/'
        backup_file = os.path.join(backup_directory, f"backup_{current_datetime}.sql")

        if not os.path.exists(backup_directory):
            os.makedirs(backup_directory)

        working_directory = backup_directory

        with open(backup_file, 'wb') as f:
            process = subprocess.Popen(
                ['mysqldump', '-u', 'ali', '--password=8540', 'alidb'],
                stdout=f,
                cwd=working_directory
            )
            process.wait()

        with open(backup_file, 'rb') as f:
            file_content = f.read()

        with io.BytesIO(file_content) as document_io:
            document_io.name = backup_file
            bot.send_document(chat_id=chat_id, document=document_io)

        bot.send_message(chat_id, "Scheduled database backup completed and sent.")


# Command: /exportocpasswd
@bot.message_handler(commands=['exportocpasswd'])
@authorized_only
def export_ocpasswd(message=None):
    try:
        if message:
            # This is the message handler version
            # Path to the 'ocpasswd' file
            ocpasswd_file_path = '/etc/ocserv/ocpasswd'
            
            # Read the contents of the 'ocpasswd' file
            with open(ocpasswd_file_path, 'rb') as ocpasswd_file:
                ocpasswd_contents = ocpasswd_file.read()
           
            # Send the contents of the 'ocpasswd' file as a message attachment
            with io.BytesIO(ocpasswd_contents) as document_io:
                document_io.name = 'ocpasswd'
                bot.send_document(message.chat.id, document=document_io)

        else:
            # This is the scheduled task version
            ocpasswd_file_path = '/etc/ocserv/ocpasswd'

            with open(ocpasswd_file_path, 'rb') as ocpasswd_file:
                ocpasswd_contents = ocpasswd_file.read()

            with open('/root/bot/ocpasswd', 'wb') as backup_file:
                backup_file.write(ocpasswd_contents)

            with open('/root/bot/ocpasswd', 'rb') as backup_file:
                document_io = io.BytesIO(backup_file.read())
                document_io.name = 'ocpasswd'
                chat_id = CHANNEL_ID  # Replace with the desired chat or channel ID
                bot.send_document(chat_id, document=document_io)

    except Exception as e:
        chat_id = CHANNEL_ID  # Replace with the desired chat or channel ID
        bot.send_message(chat_id, f"An error occurred: {str(e)}")


# Command: /restartalinet
@bot.message_handler(commands=['restartalinet'])
@authorized_only
def restart_alinet(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Restarting alinet service...")
    
    subprocess.run(['sudo', 'systemctl', 'restart', 'alinet'])
    
    bot.send_message(chat_id, "alinet service has been restarted!")



# Schedule the lock_expired_users, export_ocpasswd and backup_mysql_db functions to run every day at a specific time (e.g., 00:00)
schedule.every().day.at("02:00").do(lambda: lock_expired_users()) # 5:30 a.m in Tehran Timezone
schedule.every().day.at("22:30").do(lambda: export_ocpasswd())    # 2:00 a.m in Tehran Timezone
schedule.every().day.at("22:31").do(lambda: backup_mysql_db())    # 2:01 a.m in Tehran Timezone


# Function to run the bot's polling loop
def run_bot_polling():
    bot.polling()


# Start the bot polling loop in a separate thread
bot_thread = threading.Thread(target=run_bot_polling)
bot_thread.start()


# Run the scheduler in the main thread
while True:
    schedule.run_pending()
    time.sleep(1)

