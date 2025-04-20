# -*- coding: utf-8 -*-

import os
import logging
from typing import Dict, List, Union, Optional, Any
from cryptography.fernet import Fernet, InvalidToken
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class Config:
    """
    Configuration class to initialize and manage application settings.
    """

    def __init__(self, db: AsyncIOMotorClient) -> None:
        """
        Initialize the configuration with database connection.
        
        Args:
            db (AsyncIOMotorClient): The MongoDB client instance.
        """
        self.db = db
        self.report_min_lim: Optional[float] = None
        self.report_max_lim: Optional[float] = None
        self.report_interval: Optional[int] = None
        self.report_scan: Optional[int] = None
        self.socks5_ip: Optional[str] = None
        self.socks5_port: Optional[int] = None
        self.socks5_username: Optional[str] = None
        self.socks5_password: Optional[str] = None
        self.telegram_url: Optional[str] = None
        self.telegram_client_api_id: Optional[str] = None
        self.telegram_client_api_hash: Optional[str] = None
        self.telegram_client_commandor: Optional[str] = None
        self.telegram_api_chat_id: Optional[str] = None
        self.telegram_api_bot_name_1: Optional[str] = None
        self.telegram_api_bot_api_key_1: Optional[str] = None
        self.telegram_api_bot_name_2: Optional[str] = None
        self.telegram_api_bot_api_key_2: Optional[str] = None
        self.toolchain_geco_url: Optional[str] = None
        self.toolchain_ether_url: Optional[str] = None
        self.toolchain_ether_chain: Optional[str] = None
        self.toolchain_ether_address: Optional[str] = None
        self.toolchain_ether_api_key_1: Optional[str] = None
        self.toolchain_ether_api_key_2: Optional[str] = None
        self.token: List[Dict[str, Union[str, float, int]]] = []

        # Read the encryption key from environment variable
        self.key = os.environ.get('ENCRYPTION_KEY')
        if self.key is None:
            raise ValueError("ENCRYPTION_KEY environment variable not set")

        self.cipher_suite = Fernet(self.key.encode())
        
    def encrypt_data(self, data: str) -> str:
        """Encrypts data"""
        try:
            return self.cipher_suite.encrypt(data.encode()).decode()
        except (TypeError, ValueError) as e:
            raise ValueError(f"Error encrypting data")

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypts data"""
        try:
            return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
        except (InvalidToken, TypeError, ValueError) as e:
            raise ValueError(f"Error decrypting data")

    def is_encrypted(self, data: str) -> bool:
        """Checks if data is encrypted"""
        try:
            self.cipher_suite.decrypt(data.encode())
            return True
        except InvalidToken:
            return False

    def convert_to_string(self, data: Any) -> str:
        """Converts data to string"""
        try:
            return str(data)
        except Exception as e:
            logger.error(f"Unexpected error in convert_to_string")

    async def init_config(self) -> None:
        """Asynchronously initialize the configuration by fetching data from the database"""
        try:
            c_config = self.db.config

            # Report
            try:
                report_data = await c_config.find_one({"_id": "report"})
                if report_data:
                    self.report_min_lim = report_data.get("min_lim")
                    self.report_max_lim = report_data.get("max_lim")
                    self.report_interval = report_data.get("interval")
                    self.report_scan = report_data.get("scan")
            except Exception as e:
                print(f"Error fetching report data")

            # Socks5
            try:
                socks5_data = await c_config.find_one({"_id": "socks5"})
                if socks5_data:
                    self.socks5_ip = socks5_data.get("ip")
                    self.socks5_port = socks5_data.get("port")
                    self.socks5_username = socks5_data.get("username")
                    self.socks5_password = socks5_data.get("password")

                    # Encrypt data if not already encrypted
                    for key in ['ip', 'port', 'username', 'password']:
                        if not self.is_encrypted(self.convert_to_string(socks5_data[key])):
                            socks5_data[key] = self.encrypt_data(self.convert_to_string(socks5_data[key]))
                    await c_config.update_one({'_id': 'socks5'}, {'$set': socks5_data})

                    # Decrypt data
                    self.socks5_ip = self.decrypt_data(socks5_data.get("ip"))
                    self.socks5_port = int(self.decrypt_data(socks5_data.get("port")))
                    self.socks5_username = self.decrypt_data(socks5_data.get("username"))
                    self.socks5_password = self.decrypt_data(socks5_data.get("password"))
            except Exception as e:
                print(f"Error fetching or processing socks5 data")

            # Telegram
            try:
                telegram_data = await c_config.find_one({"_id": "telegram"})
                if telegram_data:
                    encrypted = False
                    # Encrypt data if not already encrypted
                    if "client" in telegram_data:
                        client_data = telegram_data["client"]
                        for key in ["api_id", "api_hash", "commandor"]:
                            if key in client_data and not self.is_encrypted(self.convert_to_string(client_data[key])):
                                client_data[key] = self.encrypt_data(self.convert_to_string(client_data[key]))
                                encrypted = True

                    if "api" in telegram_data:
                        api_data = telegram_data["api"]
                        if "chat_id" in api_data and not self.is_encrypted(self.convert_to_string(api_data["chat_id"])):
                            api_data["chat_id"] = self.encrypt_data(self.convert_to_string(api_data["chat_id"]))
                            encrypted = True

                        if "bot" in api_data:
                            bots_data = api_data["bot"]
                            for bot in bots_data:
                                if "api_key" in bot and not self.is_encrypted(self.convert_to_string(bot["api_key"])):
                                    bot["api_key"] = self.encrypt_data(self.convert_to_string(bot["api_key"]))
                                    encrypted = True

                    if encrypted:
                        await c_config.update_one({'_id': 'telegram'}, {'$set': telegram_data})

                    # Decrypt data
                    if "client" in telegram_data:
                        client_data = telegram_data["client"]
                        for key in ["api_id", "api_hash", "commandor"]:
                            if key in client_data:
                                client_data[key] = self.decrypt_data(client_data[key])

                    if "api" in telegram_data:
                        api_data = telegram_data["api"]
                        if "chat_id" in api_data:
                            api_data["chat_id"] = self.decrypt_data(api_data["chat_id"])

                        if "bot" in api_data:
                            bots_data = api_data["bot"]
                            for bot in bots_data:
                                if "api_key" in bot:
                                    bot["api_key"] = self.decrypt_data(bot["api_key"])

                    self.telegram_url = telegram_data.get("url")
                    self.telegram_client_api_id = telegram_data["client"].get("api_id")
                    self.telegram_client_api_hash = telegram_data["client"].get("api_hash")
                    self.telegram_client_commandor = telegram_data["client"].get("commandor")
                    self.telegram_api_chat_id = telegram_data["api"].get("chat_id")
                    self.telegram_api_bot_name_1 = telegram_data["api"]["bot"][0].get("name")
                    self.telegram_api_bot_api_key_1 = telegram_data["api"]["bot"][0].get("api_key")
                    self.telegram_api_bot_name_2 = telegram_data["api"]["bot"][1].get("name")
                    self.telegram_api_bot_api_key_2 = telegram_data["api"]["bot"][1].get("api_key")
            except Exception as e:
                print(f"Error fetching or processing telegram data")

            # Toolchain
            try:
                toolchain_data = await c_config.find_one({"_id": "toolchain"})
                if toolchain_data:
                    encrypted = False
                    if "ether" in toolchain_data:
                        ether_data = toolchain_data["ether"]
                        if "api_key" in ether_data:
                            api_key_data = ether_data["api_key"]
                            for i, key in enumerate(api_key_data):
                                if not self.is_encrypted(self.convert_to_string(key)):
                                    api_key_data[i] = self.encrypt_data(self.convert_to_string(key))
                                    encrypted = True

                    if encrypted:
                        await c_config.update_one({'_id': 'toolchain'}, {'$set': toolchain_data})

                    # Decrypt data
                    if "ether" in toolchain_data:
                        ether_data = toolchain_data["ether"]
                        if "api_key" in ether_data:
                            api_key_data = ether_data["api_key"]
                            for i, key in enumerate(api_key_data):
                                api_key_data[i] = self.decrypt_data(key)

                    self.toolchain_geco_url = toolchain_data["geco"].get("url")
                    self.toolchain_ether_url = toolchain_data["ether"].get("url")
                    self.toolchain_ether_chain = toolchain_data["ether"].get("chain")
                    self.toolchain_ether_address = toolchain_data["ether"].get("address")
                    self.toolchain_ether_api_key_1 = toolchain_data["ether"]["api_key"][0]
                    self.toolchain_ether_api_key_2 = toolchain_data["ether"]["api_key"][1]
            except Exception as e:
                print(f"Error fetching or processing toolchain data")

            # Tokens
            try:
                tokens_data = await c_config.find_one({"_id": "tokens"})
                if tokens_data:
                    token_list = tokens_data.get("token", [])
                    if token_list:
                        for item in token_list:
                            token_info = {
                                "name": item.get("name"),
                                "chain": item.get("chain"),
                                "address": item.get("address"),
                                "buy_price": item.get("buy_price"),
                                "quantity": item.get("quantity")
                            }
                            self.token.append(token_info)
            except Exception as e:
                print(f"Error fetching or processing tokens data")

        except Exception as e:
            logger.error(f"Error in init_config")