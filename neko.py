import os
import asyncio
import threading
import logging
import nest_asyncio
from arg_parser import get_args
from pyrogram import Client

from telegram_bot_interface import TelegramBotInterface
from my_server_flask import run_flask
from start_bot import start_data, start_data_2

nest_asyncio.apply()

args = get_args()

logging.basicConfig(level=logging.ERROR)

class NekoBot:
    def __init__(self):
        self.args = args
        self.telegram_bots = []
        self.flask_thread = None
        self.main_bot = None
    
    def setup_callbacks(self):
        return {
            'process_command': self.process_command_callback,
            'process_query': self.process_query_callback,
            'get_bot_manager': lambda: self
        }
    
    async def process_command_callback(self, client, message, user_id, username, chat_id):
        from command.db.db import load_user_config
        lvl_to_use = 0
        if user_id:
            try:
                lvl_user = load_user_config(user_id, "lvl")
                int_lvl_user = int(lvl_user) if lvl_user and lvl_user.isdigit() else 0
                lvl_to_use = int_lvl_user
            except Exception:
                return
        else:
            try:
                lvl_group = load_user_config(chat_id, "lvl")
                int_lvl_group = int(lvl_group) if lvl_group and lvl_group.isdigit() else 0
                lvl_to_use = int_lvl_group
            except Exception:
                return
        
        await self.process_command_with_manager(client, message, user_id, username, chat_id, lvl_to_use)
    
    async def process_command_with_manager(self, client, message, user_id, username, chat_id, lvl_to_use):
        from process_command import process_command
        await process_command(client, message, user_id, username, chat_id, lvl_to_use, self)
    
    async def process_query_callback(self, client, callback_query):
        from process_query import process_query
        await process_query(client, callback_query)
    
    def initialize_main_bot(self):
        if self.args.bot_token:
            app = Client(
                "my_bot",
                api_id=self.args.api_id,
                api_hash=self.args.api_hash,
                bot_token=self.args.bot_token,
                sleep_threshold=5,
                max_concurrent_transmissions=True
            )
        else:
            app = Client(
                "my_bot",
                api_id=self.args.api_id,
                api_hash=self.args.api_hash,
                session_string=self.args.session_string,
                sleep_threshold=5,
                max_concurrent_transmissions=True
            )
        
        callbacks = self.setup_callbacks()
        self.main_bot = TelegramBotInterface(app, self.args, callbacks)
        self.telegram_bots.append(self.main_bot)
        
        return self.main_bot
    
    async def clone_bot(self, new_bot_token, api_id=None, api_hash=None):
        try:
            api_id = api_id or self.args.api_id
            api_hash = api_hash or self.args.api_hash
            
            new_client = Client(
                name=f"bot_{new_bot_token[:10]}",
                api_id=api_id,
                api_hash=api_hash,
                bot_token=new_bot_token,
                in_memory=True,
                sleep_threshold=5,
                max_concurrent_transmissions=1
            )
            
            callbacks = self.setup_callbacks()
            new_bot_interface = TelegramBotInterface(
                client=new_client,
                args=self.args,
                callbacks=callbacks
            )
            
            success = await new_bot_interface.start()
            
            if success:
                self.telegram_bots.append(new_bot_interface)
                bot_info = await new_client.get_me()
                print(f"Bot @{bot_info.username} iniciado")
                return new_bot_interface
            else:
                return None
            
        except Exception as e:
            print(f"Error al clonar bot: {e}")
            return None
            
    def start_flask(self):
        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
        print("[INFO] Servidor Flask iniciado en puerto 5000.")
    
    def restart_flask(self):
        if self.flask_thread and self.flask_thread.is_alive():
            print("[INFO] Reiniciando servidor Flask...")
            self.start_flask()
        else:
            print("[INFO] Iniciando servidor Flask...")
            self.start_flask()
    
    async def run(self):
        if self.args.owner:
            start_data()
        start_data_2()
        
        self.start_flask()
        
        main_bot = self.initialize_main_bot()
        await main_bot.start()
        
        print("Bot principal iniciado.")
        
        await asyncio.Event().wait()
    
    async def shutdown(self):
        for bot in self.telegram_bots:
            try:
                await bot.stop()
            except Exception as e:
                print(f"[!] Error al detener bot: {e}")

bot_manager = None

async def main():
    global bot_manager
    bot_manager = NekoBot()
    
    try:
        await bot_manager.run()
    except KeyboardInterrupt:
        print("\n[INFO] Apagando bots...")
        await bot_manager.shutdown()
        print("[INFO] Bots apagados correctamente.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Detención forzada realizada")
