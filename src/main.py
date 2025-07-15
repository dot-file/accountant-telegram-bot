import telebot
from telebot.util import quick_markup
from telebot import types
from contextlib import suppress
import os
import sqlite3


BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_PATH = os.getenv("DATABASE_PATH")
MAIN_MENU_COMMANDS = {
    "lend":          "Lend",    
    "borrow":        "Borrow",  
    "give_back":     "Give back",
    "take_back":     "Take back",
    "show_debts":    "Show debts",
    "show_history":  "Show history",
}


bot = telebot.TeleBot(BOT_TOKEN)

sql_connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
sql_cursor = sql_connection.cursor()


def init_sql():
    sql_cursor.execute('''
        CREATE TABLE IF NOT EXISTS Entries (
            from_usr_id INTEGER NOT NULL,
            to_usr_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            date DATETIME UNIQUE DEFAULT (DATETIME('now'))
        )
    ''')
    
    sql_cursor.execute('''
        CREATE TABLE IF NOT EXISTS Queries (
            querier_id INTEGER NOT NULL UNIQUE,
            query TEXT NOT NULL,
            from_usr_id INTEGER,
            to_usr_id INTEGER,
            amount INTEGER
        )
    ''')

    sql_connection.commit()


def init_bot_commands():
    main_menu_commands_converted = list(
        map(
            lambda item: telebot.types.BotCommand('/' + item[0], item[1]),
            MAIN_MENU_COMMANDS.items()
        )
    )
    
    commands = [
        telebot.types.BotCommand("/start", "Main menu"),
        telebot.types.BotCommand("/show_my_id", "Show your ID"),
    ] + main_menu_commands_converted
    
    bot.set_my_commands(commands=commands)


@bot.message_handler(commands=['start'])
def on_start_command(message):
    chat_id = message.chat.id

    remove_query(querier_id=chat_id)
    send_start_message(chat_id=chat_id)


@bot.message_handler(commands=['show_my_id'])
def on_show_my_id_command(message):
    bot.send_message(
        message.chat.id,
        message.chat.id,
    )


# [*dict] returns the list of the keys of a dictionary
@bot.message_handler(commands=[*MAIN_MENU_COMMANDS])
def on_main_menu_command(message):
    handle_command(
        command=message.text[1:],
        chat_id=message.chat.id,
    )
    

@bot.message_handler(func=lambda message: True, content_types=['text'])
def on_text_message(message):
    supplement_query(
        querier_id=message.chat.id,
        new_value = message.text,
    )


@bot.callback_query_handler(func=lambda call: call.data in [*MAIN_MENU_COMMANDS])
def on_main_command_callback_query(call):
    feedback_pressed_button(call)

    chat_id = call.message.chat.id

    handle_command(
        command=call.data,
        chat_id=call.message.chat.id,
    )


@bot.callback_query_handler(func=lambda call: True)
def on_any_callback_query(call):
    supplement_query(
        querier_id=call.message.chat.id,
        new_value=call.data,
    )

    bot.answer_callback_query(call.id)
    bot.edit_message_reply_markup(
        chat_id = call.message.chat.id,
        message_id = call.message.id,
        reply_markup = None,
    )


def send_start_message(chat_id):
    buttons = dict(
        map(
            lambda item: (
                item[1],
                {"callback_data": item[0]}
            ),
            MAIN_MENU_COMMANDS.items()
        )
    )

    reply_markup = quick_markup(buttons)

    bot.send_message(
        chat_id=chat_id,
        parse_mode="HTML",
        reply_markup=reply_markup,
        text='''
<b>Welcome to Accountant Bot!</b>
This bot keeps track of debts between people.

Press a button to proceed.
        ''',
    )


def detuplize(tupled_list: list()) -> list():
    out = [item for t in tupled_list for item in t]
    return out


def get_partners(from_usr_id) -> list():
    partners = sql_cursor.execute(
        'SELECT DISTINCT `to_usr_id`, `from_usr_id` FROM `Entries` WHERE `from_usr_id` = ? OR `to_usr_id` = ?',
        (from_usr_id, from_usr_id),
    ).fetchall()

    detupled = detuplize(partners)

    deduplicated = list(set(detupled))
    if from_usr_id in deduplicated:
        deduplicated.remove(from_usr_id)

    return deduplicated


def generate_partner_markup(from_usr_id):
    partners = get_partners(from_usr_id)
    buttons = {}

    for user_id in partners:
        user_info = get_user_info(user_id, html_enable=False)
        buttons[user_info] = {
            'callback_data': user_id
        }
    markup = quick_markup(buttons)

    return markup


def update_query(querier_id, query, from_usr_id, to_usr_id, amount):
    sql_cursor.execute(
        '''
            INSERT OR REPLACE INTO `Queries` (querier_id, query, from_usr_id, to_usr_id, amount)
            VALUES (?, ?, ?, ?, ?)
        ''',
        (querier_id, query, from_usr_id, to_usr_id, amount),
    )
    sql_connection.commit()


def remove_query(querier_id):
    sql_cursor.execute(
        'DELETE FROM `Queries` WHERE `querier_id` = ?',
        (querier_id,),
    )
    sql_connection.commit()


def supplement_query(querier_id, new_value):
    if not new_value.isnumeric():
        bot.send_message(
            chat_id=querier_id,
            text="Your message should only contain a number.",
        )
        return

    pending_query = sql_cursor.execute(
        '''
            SELECT `query`, `from_usr_id`, `to_usr_id`, `amount`
            FROM `Queries` WHERE `querier_id` = ?
        ''',
        (querier_id,)
    ).fetchall()

    if not pending_query:
        send_start_message(chat_id=querier_id)
        return


    updated_query = detuplize(pending_query)

    for i in range(len(updated_query)):
        if not updated_query[i]:
            updated_query[i] = new_value
            break

    query = updated_query[0]
    from_usr_id = updated_query[1]
    to_usr_id = updated_query[2]
    amount = updated_query[3]

    process_query(querier_id, query, from_usr_id, to_usr_id, amount)


def process_query(querier_id, query, from_usr_id, to_usr_id, amount):
    text = ""
    reply_markup = None

    if not from_usr_id or not to_usr_id:
        update_query(querier_id, query, from_usr_id, to_usr_id, amount)
        reply_markup = generate_partner_markup(from_usr_id or to_usr_id)
        text = "<b>Who is the other user?</b>\n\nClick a button with the user's name.\nTo add a new user, enter their ID (they can get it with /show_my_id)"

    elif str(from_usr_id) == str(to_usr_id):
        text="You can't choose yourself. Choose someone else."
        update_query(query, from_usr_id, None, amount)

    elif query == "show_debts":
        show_debts(from_usr_id, to_usr_id)
        remove_query(querier_id)
        return

    elif query == "show_history":
        show_history(from_usr_id, to_usr_id)
        remove_query(querier_id)
        return

    elif not amount:
        update_query(querier_id, query, from_usr_id, to_usr_id, amount)
        chosen_user_info = get_user_info(from_usr_id if query == "take" else to_usr_id)
        text=f"<b>{chosen_user_info}</b> was chosen.\n\n<b>What's the amount?</b>",

    elif query in {"give", "take"}:
        give(from_usr_id, to_usr_id, amount)
        remove_query(querier_id)
        return


    bot.send_message(
        chat_id=querier_id, 
        reply_markup=reply_markup,
        parse_mode="HTML",
        text=text,
    )


def feedback_pressed_button(call):
    button_text = MAIN_MENU_COMMANDS[call.data]

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        parse_mode="HTML",
        text=f"<b>You pressed</b>: {button_text}",
    )


def show_debts(from_usr_id, to_usr_id):
    from_usr_id_entries = sql_cursor.execute(
        'SELECT `amount` FROM `Entries` WHERE `from_usr_id` = ? AND `to_usr_id` = ?',
        (from_usr_id, to_usr_id)
    ).fetchall()

    from_usr_id_sum = 0
    if from_usr_id_entries:
        from_usr_id_sum = sum(detuplize(from_usr_id_entries))

    to_usr_id_entries = sql_cursor.execute(
        'SELECT `amount` FROM `Entries` WHERE `to_usr_id` = ? AND `from_usr_id` = ?',
        (from_usr_id, to_usr_id)
    ).fetchall()

    to_usr_id_sum = 0
    if to_usr_id_entries:
        to_usr_id_sum = sum(detuplize(to_usr_id_entries))

    difference = from_usr_id_sum - to_usr_id_sum

    to_usr_id_info = get_user_info(to_usr_id)
    text = ""
    
    if difference == 0:
        text = f"No one among you and <b>{to_usr_id_info}</b> is in debt"
    elif difference < 0:
        text = f"You owe <b>{to_usr_id_info}</b>: {-difference}"
    elif difference > 0:
        text = f"<b>{to_usr_id_info}</b> owes you: {difference}"

    bot.send_message(chat_id=from_usr_id, parse_mode="HTML", text=text)


def show_history(from_usr_id, to_usr_id):
    text = "<b>Last several dozen entries</b>\n\n"

    from_usr_info = get_user_info(from_usr_id)
    to_usr_info = get_user_info(to_usr_id)

    entries = sql_cursor.execute(
        'SELECT `from_usr_id`, `to_usr_id`, `amount`, `date` FROM `Entries` WHERE from_usr_id IN (?1, ?2) AND to_usr_id IN (?1, ?2)',
        (from_usr_id, to_usr_id),
    ).fetchall()

    if not entries:
        text += "Empty :("

    for entry in entries:
        sender_receiver = entry[0:2]
        amount = entry[2]
        date = entry[3]

        row = f"{date}\n"

        print(sender_receiver)
        print(type(sender_receiver[0]))
        direction_symbol = ""
        if sender_receiver == (int(from_usr_id), int(to_usr_id)):
            # -->
            direction_symbol = "--&gt"
        elif sender_receiver == (int(to_usr_id), int(from_usr_id)):
            # <--
            direction_symbol = "&lt--"

        row += f"<b>{from_usr_info}</b> {direction_symbol} <b>{to_usr_info}</b>: <i><b>{amount}</b></i>\n\n"

        if len(text + row) >= 4096:
            break
        else:
            text += row

    bot.send_message(chat_id=from_usr_id, text=text, parse_mode="HTML")


def give(from_usr_id, to_usr_id, amount):
    sql_cursor.execute(
        'INSERT INTO `Entries` (from_usr_id, to_usr_id, amount) VALUES (?, ?, ?)',
        (from_usr_id, to_usr_id, amount),
    )
    sql_connection.commit()

    to_usr_id_info = get_user_info(to_usr_id)
    from_usr_id_info = get_user_info(from_usr_id)

    with suppress(Exception):
        bot.send_message(
            chat_id=from_usr_id,
            parse_mode="HTML",
            text=f"The amount of <b>{amount}</b> was given to <b>{to_usr_id_info}</b>"
        )
        show_debts(from_usr_id=from_usr_id, to_usr_id=to_usr_id)

    with suppress(Exception):
        bot.send_message(
            chat_id=to_usr_id,
            parse_mode="HTML",
            text=f"You have just received the amount of <b>{amount}</b> from <b>{from_usr_id_info}</b>",
        )
        show_debts(from_usr_id=to_usr_id, to_usr_id=from_usr_id)


def get_user_info(user_id, html_enable=True) -> str:
    user_info = ""

    try:
        chat = bot.get_chat(user_id)

        user_info = chat.first_name
        if chat.last_name != None:
            user_info += " " + chat.last_name
    
        username = chat.username
        if username != None:
            user_info = username

    except Exception:
        user_info = "User not found"

    user_info += f" ({user_id})"

    if html_enable:
        user_info = f"<a href=\"tg://user?id={user_id}\">{user_info}</a>"

    return user_info


def handle_command(command, chat_id):
    querier_id = chat_id
    query = ""
    from_usr_id = None
    to_usr_id = None
    amount = None

    if command in {"lend", "give_back"}:
        query = "give"
    elif command in {"borrow", "take_back"}:
        query = "take"
    else:
        query = command

    if query == "take":
        to_usr_id = querier_id
    else:
        from_usr_id = querier_id

    process_query(querier_id, query, from_usr_id, to_usr_id, amount)


def main():
    init_sql()
    init_bot_commands()
    bot.polling(non_stop=True)


if __name__ == "__main__":
    main()
