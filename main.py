import hashlib
import re

from pyrogram import Client, filters
from pyrogram.types import (Message, CallbackQuery, InlineKeyboardButton,
                            InlineKeyboardMarkup)
from pyrogram.errors.exceptions.bad_request_400 import (ChannelInvalid,
                                                        PeerIdInvalid,
                                                        UsernameNotOccupied,
                                                        UsernameInvalid)
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate

from forward import user
from config import Forwarding, Bot

# Load the bot configuration
bot_config = Bot().get_config()
forwardings = Forwarding()

# Set up the Telegram client
API_ID = bot_config["api_id"]
API_HASH = bot_config["api_hash"]

bot = Client("bot", API_ID, API_HASH)
commands = ["start", "menu", "new"]
answer_users = {}


# Lambda function to create a hash from a string
async def md5(word): return hashlib.md5(word.encode("utf-8")).hexdigest()


async def is_admin(filter, client: Client, event: Message | CallbackQuery):
    """ Check if the user is an admin"""
    id = event.chat.id if type(event) == Message else event.message.chat.id
    admins = Bot().get_config()["admins"]
    return id in admins


@bot.on_message(filters.create(is_admin) & filters.command(commands))
async def on_command(client: Client, message: Message):
    if "start" == message.command[0] or "menu" == message.command[0]:
        await menu(message, False)


@bot.on_message(filters.create(is_admin))
async def on_message(client: Client, message: Message):
    global answer_users
    user_id = message.chat.id

    if str(user_id) not in answer_users:
        answer_users[str(user_id)] = [False, None, None]
    if answer_users[str(user_id)][0]:
        answer_type = answer_users[str(user_id)][1]
        forwarder_id = answer_users[str(user_id)][2]

        if answer_type == "change_name":
            await change_name(message, forwarder_id, True)
        elif answer_type == "add_replace_word":
            await add_replace_word(message, forwarder_id, True)
        elif answer_type == "add_blocked_word":
            await add_blocked_word(message, forwarder_id, True)
        elif answer_type == "source_add":
            await source_add(message, forwarder_id, True)
        elif answer_type == "new_forwarder_target":
            await new_forwarder_get_target(message, True)
        elif answer_type == "new_forwarder_source":
            chat_id = list(forwarder_id.keys())[0]
            chat_name = forwarder_id[chat_id]
            await new_forwarder_get_source(message, chat_id, chat_name, True)


@bot.on_callback_query(filters.create(is_admin))
async def on_callback_query(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    message = callback_query.message
    user_id = message.chat.id
    answer_users[str(user_id)] = [False, None, None]

    if data == "menu":
        await menu(message)
    if data == "forwarders":
        await forwarders(message)
    if data.startswith("forwarder_"):
        id_hash = data.split("_")[-1]
        await forwarder(message, id_hash)
    if data.startswith("name_"):
        id_hash = data.split("_")[-1]
        await change_name(message, id_hash)
    if data.startswith("enabled_"):
        id_hash = data.split("_")[-1]
        await enable_forwarder(message, id_hash)
    if data.startswith("forwarding_mode_"):
        id_hash = data.split("_")[-1]
        await change_forwarding_mode(message, id_hash)
    if data.startswith("replace_words_"):
        id_hash = data.split("_")[-1]
        await change_replace_words(message, id_hash)
    if data.startswith("replace_delete_"):
        id_hash = data.split("_")[-1]
        word = data.split("_")[-2]
        await delete_replace_word(message, id_hash, word)
    if data.startswith("replace_add_"):
        id_hash = data.split("_")[-1]
        await add_replace_word(message, id_hash)
    if data.startswith("blocked_words_"):
        id_hash = data.split("_")[-1]
        await change_blocked_words(message, id_hash)
    if data.startswith("blocked_delete_"):
        id_hash = data.split("_")[-1]
        word = data.split("_")[-2]
        await delete_blocked_word(message, id_hash, word)
    if data.startswith("blocked_add_"):
        id_hash = data.split("_")[-1]
        await add_blocked_word(message, id_hash)
    if data.startswith("source_chats_"):
        id_hash = data.split("_")[-1]
        await source_chats(message, id_hash)
    if data.startswith("source_chat_"):
        id_hash = data.split("_")[-1]
        chat_id = data.split("_")[-2]
        await source_chat(message, id_hash, chat_id)
    if data.startswith("source_delete_"):
        id_hash = data.split("_")[-1]
        chat_id = data.split("_")[-2]
        await source_delete(message, id_hash, chat_id)
    if data.startswith("source_add_"):
        id_hash = data.split("_")[-1]
        await source_add(message, id_hash)
    if data.startswith("info_"):
        id_hash = data.split("_")[-1]
        await forwarder_info(message, id_hash)

    if data == "new":
        await new_forwarder_get_target(message)
    if data.startswith("delete_forwarder_"):
        id_hash = data.split("_")[-1]
        await delete_forwarder(message, id_hash, 1)
    if data.startswith("confirm_delete_forwarder_"):
        id_hash = data.split("_")[-1]
        await delete_forwarder(message, id_hash, 2)


async def menu(message: Message, edit: bool = True) -> None:
    """ Create the menu. """
    # Create the keyboard
    keyboard = [
        [{"🔥 Ver reenvíos": "forwarders"}],
        [{"➕ Crear reenvío": "new"}],
    ]
    keyboard = await create_keyboard(keyboard)
    # Create the text
    text = "Bienvenido, ¿qué quieres hacer?"

    # Send the message
    if edit:
        await message.edit(text, reply_markup=keyboard)
    else:
        await message.reply(text, reply_markup=keyboard)


async def forwarders(message: Message) -> None:
    """ Create the forwarders menu. """
    forwarders = (await forwardings.get_config())["forwarders"]

    # Create the keyboard
    keyboard = []
    for forwarder in forwarders:
        name = ("🟢 " if forwarder["enabled"] else "🔴 ") + forwarder["name"]
        forwarder_id = f"forwarder_{forwarder['target']}"
        keyboard.append([{name: forwarder_id}])
    keyboard.append([{"Atrás": "menu"}])
    keyboard = await create_keyboard(keyboard)
    # Create the text
    text = "Selecciona un reenvío"

    # Send the message
    await message.edit(text, reply_markup=keyboard)


async def forwarder(message: Message, forwarder_id: str) -> None:
    """ Forward the message to the forwarder. """
    # Get the forwarder
    forwarder = await forwardings.get_forwarder(forwarder_id)

    name = f"✏️ Nombre: {forwarder['name']}"
    enabled = "🟢 Habilitado" if forwarder["enabled"] else "🔴 Deshabilitado"
    forwarding_mode = "↪️ Modo de reenvío: "
    forwarding_mode += ("copiar" if forwarder["forwarding_mode"] == "copy" else
                        "reenviar")
    replace_words = "🔖 Palabras a reemplazar"
    blocked_words = "🚫 Palabras bloqueadas"
    source_chats = "👁 Chats de origen"

    # Create the keyboard
    keyboard = [
        [{name: f"name_{forwarder_id}"}],
        [{enabled: f"enabled_{forwarder_id}"}],
        [{forwarding_mode: f"forwarding_mode_{forwarder_id}"}],
        [{replace_words: f"replace_words_{forwarder_id}"}],
        [{blocked_words: f"blocked_words_{forwarder_id}"}],
        [{source_chats: f"source_chats_{forwarder_id}"}],
        [{"ℹ️ Información": f"info_{forwarder_id}"}],
        [{"🗑️ Eliminar": f"delete_forwarder_{forwarder_id}"}],
        [{"Atrás": "forwarders"}]
    ]
    if forwarder["forwarding_mode"] != "copy":
        keyboard.pop(3)

    text = "Configuración del reenvío"

    # Send the message
    keyboard = await create_keyboard(keyboard)
    await message.edit(text, reply_markup=keyboard)


async def change_name(message: Message, forwarder_id: str, change=False):
    """ Change the name of the forwarder. """
    user_id = message.chat.id

    # Get the forwarder
    forwarder_dict = await forwardings.get_forwarder(forwarder_id)

    if not change:
        # Create the keyboard
        keyboard = [
            [{"Atrás": f"forwarder_{forwarder_id}"}]
        ]
        keyboard = await create_keyboard(keyboard)
        # Create the text
        text = "Introduce el nuevo nombre"

        # Send the message
        await message.edit(text, reply_markup=keyboard)

        answer_users[str(user_id)] = [True, "change_name", forwarder_id,
                                      message]
    else:
        message_edit = answer_users[str(user_id)][3]
        answer = message.text
        forwarder_dict["name"] = answer
        await forwardings.update_forwarder(forwarder_dict)
        await forwarder(message_edit, forwarder_id)
        answer_users[str(user_id)] = [False, None, None, None]


async def enable_forwarder(message: Message, forwarder_id: str):
    """ Enable the forwarder. """
    # Get the forwarder
    forwarder_dict = await forwardings.get_forwarder(forwarder_id)

    forwarder_dict["enabled"] = not forwarder_dict["enabled"]
    await forwardings.update_forwarder(forwarder_dict)
    await forwarder(message, forwarder_id)


async def change_forwarding_mode(message: Message, forwarder_id: str):
    """ Change the forwarding mode of the forwarder. """
    # Get the forwarder
    forwarder_dict = await forwardings.get_forwarder(forwarder_id)

    if forwarder_dict["forwarding_mode"] == "copy":
        forwarder_dict["forwarding_mode"] = "forward"
    else:
        forwarder_dict["forwarding_mode"] = "copy"
    await forwardings.update_forwarder(forwarder_dict)
    await forwarder(message, forwarder_id)


async def change_replace_words(message: Message, forwarder_id: str):
    """ Change the replace words of the forwarder. """
    # Get the forwarder
    forwarder_dict = await forwardings.get_forwarder(forwarder_id)

    # Create the keyboard
    keyboard = []
    for word, value in forwarder_dict["replace_words"].items():
        word_md5 = await md5(word)
        keyboard.append([
            {f"{word} -> {value}":
             f"replace_delete_{word_md5}_{forwarder_id}"}])
    keyboard.append([{"Añadir": f"replace_add_{forwarder_id}"}])
    keyboard.append([{"Atrás": f"forwarder_{forwarder_id}"}])
    keyboard = await create_keyboard(keyboard)

    # Create the text
    text = "Añade una palabra para reemplazar.\n"
    text += "Para eliminar una palabra, pulsa sobre su nombre."

    # Send the message
    await message.edit(text, reply_markup=keyboard)


async def delete_replace_word(message: Message, forwarder_id: str,
                              word_md5: str):
    """ Delete a replace word from the forwarder. """
    forwarder = await forwardings.get_forwarder(forwarder_id)

    # Create the keyboard
    keyboard = []
    for source_id, source_name in forwarder["source"].items():
        name = f"{source_name} ({source_id})"
        keyboard.append([{name: f"source_chat_{source_id}"}])
    keyboard.append([{"Atrás": f"forwarder_{forwarder_id}"}])
    keyboard = await create_keyboard(keyboard)
    # Create the text
    text = "Selecciona un chat de origen."

    # Send the message
    await message.edit(text, reply_markup=keyboard)
    # Get the forwarder
    forwarder_dict = await forwardings.get_forwarder(forwarder_id)

    # Find the word by its md5
    for word in forwarder_dict["replace_words"].keys():
        if await md5(word) == word_md5:
            break

    # Delete the word
    del forwarder_dict["replace_words"][word]
    await forwardings.update_forwarder(forwarder_dict)
    await change_replace_words(message, forwarder_id)


async def add_replace_word(message: Message, forwarder_id: str, change=False):
    """ Add a replace word to the forwarder. """
    user_id = message.chat.id
    # Create the keyboard
    keyboard = [
        [{"Atrás": f"replace_words_{forwarder_id}"}]
    ]
    keyboard = await create_keyboard(keyboard)

    if not change:
        # Create the text
        text = "Introduce la palabra a reemplazar en este formato:\n"
        text += "`palabra>palabra_reemplazada`\n\n"
        text += "Puedes añadir varios reemplazos a la vez, solamente \n"
        text += "separándolos con un salto de línea.\n\n"
        text += "Ejemplo:\n"
        text += "`palabra1>palabra_reemplazada1\n"
        text += "palabra2>palabra_reemplazada2\n"
        text += "palabra3>palabra_reemplazada3`"

        # Send the message
        await message.edit(text, reply_markup=keyboard)

        answer_users[str(user_id)] = [True, "add_replace_word", forwarder_id,
                                      message]
    else:
        message_edit = answer_users[str(user_id)][3]
        answer = message.text

        # Check if the has the right format
        if ">" not in answer:
            text = "**Error:** El formato no es correcto.\n\n"
            text += f"**Texto introducido:** ```{answer}```"
            await message_edit.edit(text, reply_markup=keyboard)
            return

        # Get the words and the values to replace
        replaces = answer.split("\n")
        replaces = [replace.split(">") for replace in replaces]

        # Get the forwarder
        forwarder_dict = await forwardings.get_forwarder(forwarder_id)

        # Add the words and the values to replace
        for replace in replaces:
            word, value = replace
            forwarder_dict["replace_words"][word] = value

        # Update the forwarder
        await forwardings.update_forwarder(forwarder_dict)
        await change_replace_words(message_edit, forwarder_id)
        answer_users[str(user_id)] = [False, None, None, None]


async def change_blocked_words(message: Message, forwarder_id: str):
    """ Change the blocked words of the forwarder. """
    # Get the forwarder
    forwarder_dict = await forwardings.get_forwarder(forwarder_id)

    # Create the keyboard
    keyboard = []
    for word in forwarder_dict["blocked_words"]:
        word_md5 = await md5(word)
        keyboard.append([
            {f"{word}": f"blocked_delete_{word_md5}_{forwarder_id}"}])
    keyboard.append([{"Añadir": f"blocked_add_{forwarder_id}"}])
    keyboard.append([{"Atrás": f"forwarder_{forwarder_id}"}])
    keyboard = await create_keyboard(keyboard)

    # Create the text
    text = "Añade una palabra para reemplazar.\n"
    text += "Para eliminar una palabra, pulsa sobre su nombre."

    # Send the message
    await message.edit(text, reply_markup=keyboard)


async def delete_blocked_word(message: Message, forwarder_id: str,
                              word_md5: str):
    """ Delete a blocked word from the forwarder. """
    # Get the forwarder
    forwarder_dict = await forwardings.get_forwarder(forwarder_id)

    # Find the word by its md5
    for word in forwarder_dict["blocked_words"]:
        if await md5(word) == word_md5:
            break

    # Delete the word
    forwarder_dict["blocked_words"].remove(word)
    await forwardings.update_forwarder(forwarder_dict)
    await change_blocked_words(message, forwarder_id)


async def add_blocked_word(message: Message, forwarder_id: str, change=False):
    """ Add a blocked word to the forwarder. """
    user_id = message.chat.id
    # Create the keyboard
    keyboard = [
        [{"Atrás": f"blocked_words_{forwarder_id}"}]
    ]
    keyboard = await create_keyboard(keyboard)

    if not change:
        # Create the text
        text = "Introduce la palabra que quieras bloquear.\n\n"
        text += "Puedes añadir varios reemplazos a la vez, solamente \n"
        text += "separándolos con un salto de línea.\n\n"
        text += "Ejemplo:\n"
        text += "`palabra1\npalabra2\npalabra3`"

        # Send the message
        await message.edit(text, reply_markup=keyboard)

        answer_users[str(user_id)] = [True, "add_blocked_word", forwarder_id,
                                      message]
    else:
        message_edit = answer_users[str(user_id)][3]
        answer = message.text

        # Get the words and the values to blocked
        blockeds = answer.split("\n")

        # Get the forwarder
        forwarder_dict = await forwardings.get_forwarder(forwarder_id)

        # Add the words and the values to blocked
        for blocked in blockeds:
            forwarder_dict["blocked_words"].append(blocked)

        # Update the forwarder
        await forwardings.update_forwarder(forwarder_dict)
        await change_blocked_words(message_edit, forwarder_id)
        answer_users[str(user_id)] = [False, None, None, None]


async def source_chats(message: Message, forwarder_id) -> None:
    """ Create the forwarders menu. """
    forwarder = await forwardings.get_forwarder(forwarder_id)

    # Create the keyboard
    keyboard = []
    for source_id, source_name in forwarder["source"].items():
        name = f"{source_name}"
        keyboard.append([{name: f"source_chat_{source_id}_{forwarder_id}"}])
    keyboard.append([{"Añadir": f"source_add_{forwarder_id}"}])
    keyboard.append([{"Atrás": f"forwarder_{forwarder_id}"}])
    keyboard = await create_keyboard(keyboard)
    # Create the text
    text = "Selecciona un chat de origen."

    # Send the message
    await message.edit(text, reply_markup=keyboard)


async def source_chat(message: Message, forwarder_id: str, source_id: str):
    """ Forward the message to the forwarder. """
    # Create the keyboard
    keyboard = [
        [{"🗑️ Eliminar": f"source_delete_{source_id}_{forwarder_id}"}],
        [{"Atrás": f"source_chats_{forwarder_id}"}]
    ]

    text = "Configuración del chat de origen."
    text += await get_chat_info(source_id)

    # Update the forwarders name
    if re.search(r"\*\*Nombre:\*\* (.+)", text):
        name = re.search(r"\*\*Nombre:\*\* (.+)", text).group(1)
        forwarder_dict = await forwardings.get_forwarder(forwarder_id)
        forwarder_dict["source"][source_id] = name
        await forwardings.update_forwarder(forwarder_dict)

    # Send the message
    keyboard = await create_keyboard(keyboard)
    await message.edit(text, reply_markup=keyboard)


async def source_delete(message: Message, forwarder_id: str, source_id: str):
    """ Delete the source chat. """
    # Get the forwarder
    forwarder_dict = await forwardings.get_forwarder(forwarder_id)

    # Delete the source chat
    del forwarder_dict["source"][source_id]
    await forwardings.update_forwarder(forwarder_dict)
    await source_chats(message, forwarder_id)


async def source_add(message: Message, forwarder_id: str, change=False):
    """ Add the source chat. """
    user_id = message.chat.id
    # Create the keyboard
    keyboard = [
        [{"Atrás": f"source_chats_{forwarder_id}"}]
    ]
    keyboard = await create_keyboard(keyboard)

    if not change:
        # Create the text
        text = "Introduce el chat de origen.\n\n"
        text += "Puedes añadir chat de varias formas:\n\n"
        text += "**-Introduciendo el ID del chat**\n"
        text += "`628910404\n628910400`\n\n"
        text += "**-Introduciendo el nombre de usuario del chat**\n"
        text += "`@Nunnito\n@Python`\n\n"
        text += "**-Introduciendo algún enlace de un mensaje del chat**\n"
        text += "`https://t.me/c/1165316653/1815937\nhttps://t.me/python/1234`"
        text += "\n\n**-Reenviando un mensaje del chat**\n"

        # Send the message
        await message.edit(text, reply_markup=keyboard)

        answer_users[str(user_id)] = [True, "source_add", forwarder_id,
                                      message]
    else:
        # Message to be edited
        message_edit = answer_users[str(user_id)][3]
        # Get the forwarder
        forwarder_dict = await forwardings.get_forwarder(forwarder_id)

        # Get all the chats ids
        chats_ids, invalid_ids = await get_chats_id(message)

        # Add the chats and the values to source chat
        for chat_id, name in chats_ids.items():
            forwarder_dict["source"][chat_id] = name

        # Create the text
        text = ""
        if chats_ids:
            text = "Se han añadido los siguientes chats de origen:\n"
            for chat_id, name in chats_ids.items():
                text += f"**{name}**\n"
        if invalid_ids:
            text += "\n\nLos siguientes chats no se han añadido:\n"
            for chat_id in invalid_ids:
                text += f"**{chat_id}**\n"

        # Update the forwarder
        await forwardings.update_forwarder(forwarder_dict)
        # Send the message
        await message_edit.edit(text, reply_markup=keyboard)
        answer_users[str(user_id)] = [False, None, None, None]


async def forwarder_info(message: Message, forwarder_id: str):
    """ Create the forwarders menu. """
    # Create the keyboard
    keyboard = [
        [{"Atrás": f"forwarder_{forwarder_id}"}]
    ]
    keyboard = await create_keyboard(keyboard)

    # Create the text
    text = await get_chat_info(forwarder_id)

    # Send the message
    await message.edit(text, reply_markup=keyboard)


async def new_forwarder_get_target(message: Message, change=False):
    """ Create a new forwarder. """
    user_id = message.chat.id
    # Create the keyboard
    keyboard = [
        [{"Atrás": "menu"}]
    ]
    keyboard = await create_keyboard(keyboard)

    if not change:
        # Create the text
        text = "Introduce el chat de destino.\n\n"
        text += "Puedes añadir chat de varias formas:\n\n"
        text += "**-Introduciendo el ID del chat**\n"
        text += "`628910404`\n\n"
        text += "**-Introduciendo el nombre de usuario del chat**\n"
        text += "`@Nunnito`\n\n"
        text += "**-Introduciendo algún enlace de un mensaje del chat**\n"
        text += "`https://t.me/c/1165316653/1815937`"
        text += "\n\n**-Reenviando un mensaje del chat**\n"

        # Send the message
        await message.edit(text, reply_markup=keyboard)

        answer_users[str(user_id)] = [True, "new_forwarder_target", None,
                                      message]
    else:
        # Message to be edited
        message_edit = answer_users[str(user_id)][3]

        # Get all the chats ids
        chats_ids, invalid_ids = await get_chats_id(message)
        if not chats_ids:
            text = "El chat de destino no es válido."
            await message_edit.edit(text, reply_markup=keyboard)
            answer_users[str(user_id)] = [False, None, None, None]
            return
        elif await forwardings.get_forwarder(list(chats_ids.keys())[0]):
            text = "El chat de destino ya está en uso."
            await message_edit.edit(text, reply_markup=keyboard)
            answer_users[str(user_id)] = [False, None, None, None]
            return
        else:
            # Get the chat id
            chat_id = list(chats_ids.keys())[0]
            # Get the chat name
            chat_name = chats_ids[chat_id]

            await new_forwarder_get_source(message_edit, chat_id, chat_name)


async def new_forwarder_get_source(message: Message, forwarder_id: str,
                                   forwarder_name: str, change=False):
    """ Create a new forwarder. """
    user_id = message.chat.id
    # Create the keyboard
    keyboard = [
        [{"Atrás": "forwarders"}]
    ]
    keyboard = await create_keyboard(keyboard)

    if not change:
        # Create the text
        text = "Excelente, ahora introduce el chat de destino.\n\n"
        text += "Se añade de una manera muy similar al de chat de origen, "
        text += "la única diferencia es que puedes añadir más de uno.\n\n"
        text += "Puedes añadir chat de varias formas:\n\n"
        text += "**-Introduciendo el ID del chat**\n"
        text += "`628910404\n628910400`\n\n"
        text += "**-Introduciendo el nombre de usuario del chat**\n"
        text += "`@Nunnito\n@Python`\n\n"
        text += "**-Introduciendo algún enlace de un mensaje del chat**\n"
        text += "`https://t.me/c/1165316653/1815937\nhttps://t.me/python/1234`"
        text += "\n\n**-Reenviando un mensaje del chat**\n"

        # Send the message
        await message.edit(text, reply_markup=keyboard)

        answer_users[str(user_id)] = [True, "new_forwarder_source",
                                      {forwarder_id: forwarder_name}, message]
    else:
        # Message to be edited
        message_edit = answer_users[str(user_id)][3]

        # Get all the chats ids
        sources, invalid_ids = await get_chats_id(message)
        if not sources:
            text = "El chat de origen no es válido."
            await message_edit.edit(text, reply_markup=keyboard)
            answer_users[str(user_id)] = [False, None, None, None]
            return

        # Create the text
        text = ""
        if sources:
            text = "Se han añadido los siguientes chats de origen:\n"
            for chat_id, name in sources.items():
                text += f"**{name}**\n"
        if invalid_ids:
            text += "\n\nLos siguientes chats no se han añadido:\n"
            for chat_id in invalid_ids:
                text += f"**{chat_id}**\n"

        await forwardings.add_forwarder(forwarder_name, forwarder_id, sources)
        # Send the message
        await message_edit.edit(text, reply_markup=keyboard)
        answer_users[str(user_id)] = [False, None, None, None]


async def delete_forwarder(message: Message, forwarder_id: str, step=1):
    """ Delete a forwarder. """
    if step == 1:
        # Create the keyboard
        keyboard = [
            [{"Sí, seguro": f"confirm_delete_forwarder_{forwarder_id}"}],
            [{"No, cancelar": f"forwarder_{forwarder_id}"}]
        ]
        keyboard = await create_keyboard(keyboard)

        # Create the text
        text = "¿Estás seguro de que quieres eliminarlo?"
        text += await get_chat_info(forwarder_id)

        # Send the message
        await message.edit(text, reply_markup=keyboard)
    elif step == 2:
        # Delete the forwarder
        await forwardings.remove_forwarder(forwarder_id)

        # Return to the forwarders menu
        await forwarders(message)


async def create_keyboard(buttons: list) -> InlineKeyboardMarkup:
    """ Create a keyboard with the given buttons.

    Parameters
    ----------
    buttons : list
        A list with the buttons to create.
        The keys are the button text and the values are the callback data.

    Returns
    -------
    InlineKeyboardMarkup
        The keyboard with the given buttons.
    """
    keyboard = []
    # Create the buttons
    for i, button_index in enumerate(buttons):
        keyboard.append([])
        for button in button_index:
            for key, value in button.items():
                keyboard[i].append(InlineKeyboardButton(key, value))

    return InlineKeyboardMarkup(keyboard)


async def get_chat_info(chat_id: str) -> str:
    # Create the text
    try:
        chat_info = await user.get_chat(chat_id)
        if chat_info.type == "channel" or chat_info.type == "supergroup":
            chat_type = "Canal" if chat_info.type == "channel" else "Grupo"
            text = f"\n\n**Nombre:** {chat_info.title}"
            text += f"\n**ID:** `{chat_info.id}`"
            text += f"\n**Tipo:** {chat_type}"
            if chat_info.username:
                text += f"\n**Nombre de usuario:** @{chat_info.username}"
            text += f"\n**Conteo de miembros:** {chat_info.members_count}"
            text += "\n**Contenido protegido:** "
            text += "Sí" if chat_info.has_protected_content else "No"
        elif chat_info.type == "private":
            text = f"\n\n**Nombre:** {chat_info.first_name}"
            if chat_info.last_name:
                text += f" {chat_info.last_name}"
            text += f"\n**ID:** `{chat_info.id}`"
            text += "\n**Tipo:** Privado"
            if chat_info.username:
                text += f"\n**Nombre de usuario:** @{chat_info.username}"
        elif chat_info.type == "bot":
            text = f"\n\n**Nombre:** {chat_info.first_name}"
            text += f"\n**ID:** `{chat_info.id}`"
            text += "\n**Tipo:** Bot"
            text += f"\n**Nombre de usuario:** @{chat_info.username}"
    except (ChannelInvalid, ChannelPrivate, PeerIdInvalid,
            UsernameNotOccupied):
        text = "\n\n**Error:** No se ha podido obtener la información del "
        text += "chat.\n**Motivo:** El chat no existe o no estás en él.\n"
        text += f"**ID:** `{chat_id}`"

    return text


async def get_chats_id(message: Message) -> list | bool:
    """ Get the chat IDs from the given chats. """
    if message.forward_from_chat:
        name = message.forward_from_chat.title
        chats_ids = {message.forward_from_chat.id: name}
        return chats_ids, None
    elif message.forward_from:
        name = message.forward_from.first_name
        if message.forward_from.last_name:
            name += f" {message.forward_from.last_name}"
        chats_ids = {message.forward_from.id: name}
        return chats_ids, None
    else:
        chats_ids = {}
        invalid_ids = []
        chats = message.text.split("\n")
        for chat in chats:
            chat_id = None
            chat_id_url = re.search(r"https://t.me/c/(\d+)/\d+", chat)
            chat_username_url = re.search(r"https://t.me/(\w+)/\d+", chat)
            is_username = re.search(r"^@?\w+", chat)
            if chat_id_url:
                chat_id = f"-100{chat_id_url.group(1)}"
            elif chat_username_url:
                chat_id = chat_username_url.group(1)
            elif is_username:
                chat_id = is_username.group(0)
            elif chat.isnumeric():
                chat_id = chat
            else:
                invalid_ids.append(chat)

            if chat_id:
                try:
                    chat_info = await user.get_chat(chat_id)
                    chat_id = str(chat_info.id)
                    if chat_info.title:
                        name = chat_info.title
                    else:
                        name = chat_info.first_name
                        name += f" {chat_info.last_name}" if\
                            chat_info.last_name else ""
                    chats_ids[chat_id] = name
                except (ChannelInvalid, ChannelPrivate, PeerIdInvalid,
                        UsernameNotOccupied, UsernameInvalid):
                    invalid_ids.append(chat_id)

        return chats_ids, invalid_ids


user.start()
bot.run()