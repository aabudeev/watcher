# -*- coding: utf-8 -*-

import asyncio
import logging
import subprocess
from typing import Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.error import TimedOut, NetworkError
from watcher_requests import Requests
import watcher_utility as Util

logger = logging.getLogger(__name__)

class TelegramBot:
    """
    Class for handling all Telegram bot interactions.
    """
    
    @staticmethod
    async def notify_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Notify the admin about an unauthorized user."""
        try:
            message = (
                f"<code>Неавторизованный пользователь:\n</code>"
                f"<code>ID:        {update.effective_chat.id}\n</code>"
                f"<code>Имя:       {update.effective_user.first_name}\n</code>"
                f"<code>Сообщение: {update.effective_message.text}</code>"
            )

            await Requests.send_message(context.bot_data['config'], message)
            logger.info("Admin notified about unauthorized user")
        except AttributeError as e:
            logger.error(f"AttributeError in notify_admin: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in notify_admin: {e}")

    @staticmethod
    async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command."""
        try:
            if update.effective_chat.id == context.bot_data['admin_id']:
                keyboard = [
                    [InlineKeyboardButton("Цена газа в сети Eth", callback_data='gas')],
                    [InlineKeyboardButton("Сводная информация", callback_data='info')],
                    [InlineKeyboardButton("Получить логи", callback_data='log_file')],
                    [InlineKeyboardButton("Перезапустить бота", callback_data='restart')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text('Меню бота:', reply_markup=reply_markup)
            else:
                await TelegramBot.notify_admin(update, context)
                logger.warning(f"Unauthorized access attempt by user ID: {update.effective_chat.id}")
        except AttributeError as e:
            logger.error(f"AttributeError in handle_help: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in handle_help: {e}")

    @staticmethod
    async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button clicks from the inline keyboard."""
        query = update.callback_query
        await query.answer()

        try:
            if query.data == 'gas':
                await TelegramBot.handle_gas(update, context)
            elif query.data == 'info':
                await TelegramBot.handle_info(update, context)
            elif query.data == 'log_file':
                await TelegramBot.handle_log_file(update, context)
            elif query.data == 'restart':
                await TelegramBot.handle_restart(update, context)
            elif query.data == 'start':
                await TelegramBot.handle_start(update, context)
            else:
                await TelegramBot.notify_admin(update, context)
                logger.warning(f"Unknown button click data: {query.data}")
        except AttributeError as e:
            logger.error(f"AttributeError in button: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in button: {e}")

    @staticmethod
    async def handle_gas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the 'gas' button click."""
        try:
            if update.effective_chat.id == context.bot_data['admin_id']:
                db_ops = context.bot_data['db_ops']
                gas_price = await db_ops.get_latest_gas_price()
                await Requests.send_message(context.bot_data['config'], f"<code>{gas_price}$</code>")
            else:
                await TelegramBot.notify_admin(update, context)
                logger.warning(f"Unauthorized access attempt by user ID: {update.effective_chat.id}")
        except AttributeError as e:
            logger.error(f"AttributeError in handle_gas: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in handle_gas: {e}")

    @staticmethod
    async def handle_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the 'info' button click."""
        try:
            if update.effective_chat.id == context.bot_data['admin_id']:
                db_ops = context.bot_data['db_ops']
                config = context.bot_data['config']

                latest_entry = await db_ops.get_latest_entry()
                if latest_entry:
                    worth = Util.get_worth(config, latest_entry)
                    message = Util.format_msg_report(worth, latest_entry)
                    await Requests.send_message(context.bot_data['config'], message)
                else:
                    await Requests.send_message(context.bot_data['config'], "Нет данных для отображения.")
                    logger.info("No data available in the database.")
            else:
                await TelegramBot.notify_admin(update, context)
                logger.warning(f"Unauthorized access attempt by user ID: {update.effective_chat.id}")
        except AttributeError as e:
            logger.error(f"AttributeError in handle_info: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in handle_info: {e}")

    @staticmethod
    async def handle_log_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the 'log_file' button click."""
        try:
            if update.effective_chat.id == context.bot_data['admin_id']:
                await Requests.send_document(context.bot_data['config'], "watcher.log")
            else:
                await TelegramBot.notify_admin(update, context)
                logger.warning(f"Unauthorized access attempt by user ID: {update.effective_chat.id}")
        except AttributeError as e:
            logger.error(f"AttributeError in handle_log_file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in handle_log_file: {e}")

    @staticmethod
    async def handle_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the 'restart' button click."""
        try:
            if update.effective_chat.id == context.bot_data['admin_id']:
                await Requests.send_message(context.bot_data['config'], f"<code>Перезапускаю...</code>")
                logger.info("Attempting to restart the service.")
                
                try:
                    subprocess.run(["sudo", "systemctl", "restart", "watcher.service"], check=True)
                except subprocess.CalledProcessError as e:
                    await Requests.send_message(context.bot_data['config'], f"<code>Что-то пошло не так: {e}</code>")
                    logger.error(f"Error while restarting service: {e}")
            else:
                await TelegramBot.notify_admin(update, context)
                logger.warning(f"Unauthorized access attempt by user ID: {update.effective_chat.id}")
        except AttributeError as e:
            logger.error(f"AttributeError in handle_restart: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in handle_restart: {e}")

    @staticmethod
    async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the 'start' button click."""
        try:
            if update.effective_chat.id == context.bot_data['admin_id']:
                await Requests.send_message(context.bot_data['config'], f"<code>Запущен</code>")
            else:
                await TelegramBot.notify_admin(update, context)
                logger.warning(f"Unauthorized access attempt by user ID: {update.effective_chat.id}")
        except AttributeError as e:
            logger.error(f"AttributeError in handle_start: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in handle_start: {e}")

    @staticmethod
    async def get_updates_with_retry(application: Any, retries: int = 5, initial_delay: int = 2) -> None:
        """Attempt to start the updater with retries in case of network errors."""
        delay = initial_delay
        for attempt in range(retries):
            try:
                await application.updater.start_polling()
                return
            except (NetworkError, TimedOut) as e:
                logger.error(f"Network error or timeout: {e}. Attempt {attempt + 1} of {retries}")
                if attempt + 1 < retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    raise