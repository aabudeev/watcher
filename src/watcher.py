#!venv/bin/python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from motor.motor_asyncio import AsyncIOMotorClient
from telegram.error import TimedOut, NetworkError
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from watcher_config import Config
from watcher_database import DatabaseOperations
from watcher_scheduler import Scheduler
from watcher_telegram_bot import TelegramBot
from watcher_requests import Requests

logger = logging.getLogger(__name__)

async def initialize_application(config: Config, db_ops: DatabaseOperations) -> Application:
    """Initialize and configure the Telegram bot application."""
    application = Application.builder().token(config.telegram_api_bot_api_key_2).read_timeout(30).build()
    application.bot_data['config'] = config
    application.bot_data['db_ops'] = db_ops
    application.bot_data['admin_id'] = int(config.telegram_api_chat_id)

    # Add command handlers
    application.add_handler(CommandHandler("help", TelegramBot.handle_help))
    application.add_handler(CommandHandler("gas", TelegramBot.handle_gas))
    application.add_handler(CommandHandler("info", TelegramBot.handle_info))
    application.add_handler(CommandHandler("restart", TelegramBot.handle_restart))
    application.add_handler(CommandHandler("start", TelegramBot.handle_start))
    application.add_handler(CallbackQueryHandler(TelegramBot.button))

    return application

async def setup_scheduler(config: Config, db_ops: DatabaseOperations) -> AsyncIOScheduler:
    """Set up and configure the scheduler for periodic tasks."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        Scheduler.collect, 
        'interval', 
        seconds=config.report_scan, 
        args=[config, db_ops]
    )
    return scheduler

async def run_main_loop() -> None:
    """Main application loop."""
    try:
        # Initialize MongoDB client and database
        mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = mongo_client['watcher']

        # Initialize configuration
        config = Config(db)
        await config.init_config()
        logger.info("Config initialized")

        # Initialize database operations
        db_ops = DatabaseOperations(db)

        await Requests.send_message(config, f"<code>В сети</code>")

        # Initial data collection
        await Scheduler.collect(config, db_ops)

        # Set up the Telegram bot
        application = await initialize_application(config, db_ops)
        await application.initialize()
        await application.start()
        try:
            await TelegramBot.get_updates_with_retry(application)
        except (NetworkError, TimedOut) as e:
            logger.error(f"Failed to get updates after retries: {e}")

        # Set up the scheduler
        scheduler = await setup_scheduler(config, db_ops)
        scheduler.start()

        # Keep the application running
        await asyncio.Event().wait()

        # Periodic tasks
        while True:
            await asyncio.sleep(config.report_scan)

    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        raise

if __name__ == "__main__":
    """The entry point for the script."""
    try:
        logger.info("Watcher started")
        asyncio.run(run_main_loop())
    except (KeyboardInterrupt, SystemExit) as e:
        logger.info(f"Watcher stopped due to {type(e).__name__}")
    except Exception as e:
        logger.error(f"[main] Unexpected error: {e}")