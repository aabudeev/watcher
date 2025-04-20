# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional
from aiohttp_socks import ProxyConnector
from watcher_config import Config

logger = logging.getLogger(__name__)

class Requests:
    """
    Class for handling all HTTP requests and Telegram messaging functionality.
    """
    
    @staticmethod
    async def make_request(method: str, url: str, params: Optional[Dict] = None,
                         headers: Optional[Dict] = None, files: Optional[Dict] = None,
                         proxy: Optional[str] = None, retries: int = 5, delay: int = 1) -> Optional[Dict[str, Any]]:
        """Perform an HTTP request with retries and error handling."""
        connector = ProxyConnector.from_url(proxy) if proxy else None

        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            for i in range(retries):
                try:
                    if files:
                        data = aiohttp.FormData()
                        for key, file in files.items():
                            data.add_field(key, file, filename=file.name)
                        async with session.request(method, url, data=data, params=params) as response:
                            response.raise_for_status()
                            return await response.json()
                    else:
                        async with session.request(method, url, params=params, json=params) as response:
                            response.raise_for_status()
                            return await response.json()
                except aiohttp.ClientResponseError as e:
                    if e.status in {429, 502}:
                        logger.error(f"HTTP error {e.status} while making request")
                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        logger.error(f"HTTP error {e.status} while making request")
                        break
                except aiohttp.ClientConnectionError as e:
                    logger.error(f"Connection error while making request")
                except aiohttp.ClientError as e:
                    logger.error(f"Unexpected error while making request")
                except asyncio.TimeoutError:
                    logger.error("Timeout while making request")
                except Exception as e:
                    logger.error(f"Unhandled error while making request")
                    break
            return None

    @staticmethod
    async def send_message(config: Config, msg: str) -> Optional[Dict[str, Any]]:
        """Send a message to the specified Telegram chat using the bot API."""
        url = f"{config.telegram_url}/bot{config.telegram_api_bot_api_key_2}/sendMessage"
        params = {
            'chat_id': config.telegram_api_chat_id,
            'text': msg,
            'parse_mode': 'html'
        }
        try:
            proxy = Util.get_socks5_url(config)
            return await Requests.make_request(method="POST", url=url, params=params, proxy=proxy)
        except Exception as e:
            logger.error(f"Unhandled error in send_message")
            return None

    @staticmethod
    async def send_document(config: Config, file_path: str) -> None:
        """Send a file to the specified Telegram chat using the bot API."""
        try:
            url = f"{config.telegram_url}/bot{config.telegram_api_bot_api_key_2}/sendDocument"
            params = {
                'chat_id': config.telegram_api_chat_id
            }
            proxy = Util.get_socks5_url(config)

            with open(file_path, 'rb') as file:
                files = {'document': file}
                response = await Requests.make_request(
                    method="POST",
                    url=url,
                    params=params,
                    files=files,
                    proxy=proxy
                )

            if response:
                logger.info(f"File {file_path} sent successfully.")
            else:
                logger.error(f"Failed to send file {file_path}.")

        except Exception as e:
            logger.error(f"Unhandled error in send_document")

    @staticmethod
    async def send_report(config: Config, entry: Dict[str, Any]) -> None:
        """Send a report message to the specified Telegram chat using the bot API."""
        report = entry.get("report", [])
        if report:
            if len(report) > 0:
                logger.info(f"Report sent for {len(report)} token[s]")
                logger.info(f"{json.dumps(report, indent=2, ensure_ascii=False)}")

            for item in report:
                report_msg = Util.format_msg_inform(config, item)
                await Requests.send_message(config, report_msg)
                await asyncio.sleep(config.report_interval)

            logger.info("Report sending completed")

    @staticmethod
    async def get_token_data(config: Config, entry: Optional[Dict[str, List[str]]] = None) -> List[Dict[str, Any]]:
        """Fetch token data from the specified URLs using the provided configuration."""
        proxy = Util.get_socks5_url(config)
        all_responses = []

        try:
            if entry:
                tasks = []
                for chain, addresses in entry.items():
                    address_str = "%2C".join(addresses)
                    url = f"{config.toolchain_geco_url}/{chain}/tokens/multi/{address_str}"
                    tasks.append(Requests.make_request(method="GET", url=url, proxy=proxy))

                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for response in responses:
                    if isinstance(response, Exception):
                        logger.error(f"Error fetching data: {response}")
                    elif response:
                        all_responses.extend(response.get("data", []))
            else:
                url = f"{config.toolchain_ether_url}?module=gastracker&action=gasoracle&apikey={config.toolchain_ether_api_key_1}"
                response = await Requests.make_request(method="GET", url=url, proxy=proxy)
                if response:
                    all_responses.append(response)

            return all_responses
        except Exception as e:
            logger.error(f"Unhandled error in get_token_data")
            return None

    @staticmethod
    async def get_gas_price(config: Config) -> Optional[float]:
        """Fetch the current gas price in USD."""
        try:
            gas_data_list = await Requests.get_token_data(config)

            if not gas_data_list or "result" not in gas_data_list[0] or "FastGasPrice" not in gas_data_list[0]['result']:
                logger.warning("Gas data list is empty or missing expected keys")
                return None

            gas_data = gas_data_list[0]['result']
            gwei = float(gas_data['FastGasPrice'])

            entry = {
                config.toolchain_ether_chain: [config.toolchain_ether_address]
            }

            token_data_list = await Requests.get_token_data(config, entry)

            if not token_data_list or not token_data_list[0] or "attributes" not in token_data_list[0]:
                logger.warning("Token data list is empty or missing expected keys")
                return None

            token_data = token_data_list[0]
            if "attributes" not in token_data:
                logger.warning("Token data is missing 'attributes'")
                return None
            
            price = float(token_data['attributes']['price_usd'])

            gas_price_usd = round(float(gwei * 356190 * 0.000000001 * price), 2)
            return gas_price_usd

        except Exception as e:
            logger.error(f"Unexpected error in get_gas_price")
            return None