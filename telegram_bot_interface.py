import time
import asyncio
import random
import sqlite3
import os
from pyrogram import Client, filters

class TelegramBotInterface:
    def __init__(self, client, args, callbacks):
        self.app = client
        self.args = args
        self.callbacks = callbacks
        self.bot_is_sleeping = False
        self.sleep_duration = 0
        self.start_sleep_time = 0
        self.cmd_list_initialized = False
        
    def is_bot_public(self):
        ruta_db = os.path.join(os.getcwd(), 'bot_cmd.db')
        if not os.path.exists(ruta_db):
            return False
        try:
            conn = sqlite3.connect(ruta_db)
            cursor = conn.cursor()
            cursor.execute('SELECT valor FROM parametros WHERE nombre = ?', ('public',))
            resultado = cursor.fetchone()
            conn.close()
            if not resultado:
                return False
            return int(resultado[0]) == 1
        except Exception as e:
            print(f"[!] Error al acceder a bot_cmd.db: {e}")
            return False

    def format_time(self, seconds):
        years = seconds // (365 * 24 * 3600)
        days = (seconds % (365 * 24 * 3600)) // (24 * 3600)
        hours = (seconds % (24 * 3600)) // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        result = []
        if years: result.append(f"{years} año" if years == 1 else f"{years} años")
        if days: result.append(f"{days} día" if days == 1 else f"{days} días")
        if hours: result.append(f"{hours} hora" if hours == 1 else f"{hours} horas")
        if minutes: result.append(f"{minutes} minuto" if minutes == 1 else f"{minutes} minutos")
        if seconds: result.append(f"{seconds} segundo" if seconds == 1 else f"{seconds} segundos")
        return ", ".join(result)

    def setup_handlers(self):
        @self.app.on_message(filters.text)
        async def handle_message(client, message):
            await self._handle_message(client, message)

        @self.app.on_callback_query()
        async def callback_handler(client, callback_query):
            await self._handle_callback(client, callback_query)

    async def _handle_message(self, client, message):
        if not self.cmd_list_initialized and getattr(self.args, "bot_token", None):
            try:
                from cmd_list import lista_cmd
                await lista_cmd(self.app)
                self.cmd_list_initialized = True
            except Exception as e:
                if "USER_BOT_REQUIRED" in str(e):
                    self.cmd_list_initialized = True
                else:
                    raise

        is_anonymous = message.sender_chat is not None and message.from_user is None
        user_id = message.from_user.id if message.from_user else None
        username = message.from_user.username if message.from_user else ""
        chat_id = message.chat.id if message.chat else ""

        await self._process_filters(message, chat_id, user_id, is_anonymous)

        if await self._handle_sleep_logic(message, chat_id):
            return

        bot_manager = self.callbacks.get('get_bot_manager', lambda: None)()
        await self.callbacks['process_command'](client, message, user_id, username, chat_id)

    async def _handle_callback(self, client, callback_query):
        await self.callbacks['process_query'](client, callback_query)

    async def _process_filters(self, message, chat_id, user_id, is_anonymous):
        raw_group_ids = getattr(self.args, "group_id", []) or []
        group_ids = list(map(int, raw_group_ids.split(","))) if isinstance(raw_group_ids, str) else raw_group_ids

        raw_black_words = getattr(self.args, "black_words", []) or []
        black_words = raw_black_words.split(",") if isinstance(raw_black_words, str) else raw_black_words

        raw_free_users = getattr(self.args, "free_users", []) or []
        free_users = list(map(int, raw_free_users.split(","))) if isinstance(raw_free_users, str) else raw_free_users

        raw_safe_block = getattr(self.args, "safe_block", "") or ""
        safe_block = raw_safe_block.split(",") if isinstance(raw_safe_block, str) else raw_safe_block

        if chat_id in group_ids and (message.text or message.caption):
            content = (message.text or "") + " " + (message.caption or "")
            words = content.lower().split(" ")

            should_block = False
            for word in words:
                for black in black_words:
                    if black in word:
                        if not any(safe.strip().lower() in word for safe in safe_block):
                            should_block = True
                            break
                if should_block:
                    break

            if should_block and not (is_anonymous or user_id in free_users):
                try:
                    await message.delete()
                except Exception:
                    pass

    async def _handle_sleep_logic(self, message, chat_id):
        from data.stickers import STICKER_DESCANSO, STICKER_REACTIVADO
        
        lvl_to_use = await self._get_user_level(message)
        
        if message.text and message.text.startswith("/reactive") and lvl_to_use == 6:
            if self.bot_is_sleeping:
                self.bot_is_sleeping = False
                await self.app.send_sticker(chat_id, sticker=random.choice(STICKER_REACTIVADO))
                await message.reply("Ok, estoy de vuelta.")
            return True

        if self.bot_is_sleeping and self.start_sleep_time:
            remaining = max(0, self.sleep_duration - int(time.time() - self.start_sleep_time))
            await self.app.send_sticker(chat_id, sticker=random.choice(STICKER_DESCANSO))
            await message.reply(f"Actualmente estoy descansando, no recibo comandos.\n\nRegresaré en {self.format_time(remaining)}")
            return True

        if message.text and message.text.startswith("/sleep") and lvl_to_use == 6:
            try:
                self.sleep_duration = int(message.text.split(" ")[1])
                self.bot_is_sleeping = True
                self.start_sleep_time = time.time()
                await message.reply(f"Ok, voy a descansar {self.format_time(self.sleep_duration)}.")
                await asyncio.sleep(self.sleep_duration)
                self.bot_is_sleeping = False
                await self.app.send_sticker(chat_id, sticker=random.choice(STICKER_REACTIVADO))
                await message.reply("Ok, estoy de vuelta.")
            except ValueError:
                await message.reply("Por favor, proporciona un número válido en segundos.")
            return True

        return False

    async def _get_user_level(self, message):
        from command.db.db import load_user_config
        
        user_id = message.from_user.id if message.from_user else None
        chat_id = message.chat.id if message.chat else ""
        
        if user_id:
            try:
                lvl_user = load_user_config(user_id, "lvl")
                int_lvl_user = int(lvl_user) if lvl_user and lvl_user.isdigit() else 0
                return int_lvl_user
            except Exception:
                return 0
        else:
            try:
                lvl_group = load_user_config(chat_id, "lvl")
                int_lvl_group = int(lvl_group) if lvl_group and lvl_group.isdigit() else 0
                return int_lvl_group
            except Exception:
                return 0

    async def start(self):
        try:
            await self.app.start()
            self.setup_handlers()
            me = await self.app.get_me()
            print(f"Bot iniciado: @{me.username}")
            return True
        except Exception as e:
            print(f"Error al iniciar bot: {e}")
            return False
            
    async def stop(self):
        await self.app.stop()

    def create_new_bot(self, bot_token, api_id, api_hash):
        new_client = Client(
            f"bot_{bot_token[:10]}",
            api_id=api_id,
            api_hash=api_hash,
            bot_token=bot_token,
            sleep_threshold=5,
            max_concurrent_transmissions=True
        )
        
        new_interface = TelegramBotInterface(
            client=new_client,
            args=self.args,
            callbacks=self.callbacks
        )
        
        return new_interface

    async def add_bot_instance(self, bot_token, api_id=None, api_hash=None):
        api_id = api_id or self.args.api_id
        api_hash = api_hash or self.args.api_hash
        
        new_bot = self.create_new_bot(bot_token, api_id, api_hash)
        await new_bot.start()
        return new_bot
