# -*- coding: utf-8 -*-

import logging
from typing import Dict, List, Any
from watcher_config import Config
from watcher_database import DatabaseOperations
from watcher_requests import Requests
import watcher_utility as Util

logger = logging.getLogger(__name__)

class Scheduler:
    """
    Class for scheduling and processing token data collection tasks.
    """
    
    @staticmethod
    async def parse_token_data(token_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse token data to extract relevant attributes."""
        parsed_data = []
        try:
            for token in token_data:
                attributes = token.get('attributes', {})
                decimals = attributes.get('decimals')
                price_usd = attributes.get('price_usd')
                fdv_usd = attributes.get('fdv_usd')
                volume_usd = attributes.get('volume_usd', {}).get('h24')

                parsed_data.append({
                    'address': attributes.get('address'),
                    'decimals': decimals,
                    'price_usd': price_usd,
                    'fdv_usd': fdv_usd,
                    'volume_usd': volume_usd
                })
        except Exception as e:
            logger.error(f"Unexpected error in parse_token_data")

        return parsed_data

    @staticmethod
    async def merge_chain_addr(config: Config) -> Dict[str, List[str]]:
        """Merge token addresses by their respective chains."""
        try:
            chain_addr: Dict[str, List[str]] = {}
            for item in config.token:
                chain = item['chain']
                address = item['address']
                if chain not in chain_addr:
                    chain_addr[chain] = []
                chain_addr[chain].append(address)

            return chain_addr
        except Exception as e:
            logger.error(f"Unexpected error in merge_chain_addr")
            return {}

    @staticmethod
    async def merge_data(config: Config, token_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge token data from the configuration with parsed token data."""
        try:
            tokens = config.token
            token_dict = {token['address'].lower(): token for token in tokens}
            
            parsed_token_data = await Scheduler.parse_token_data(token_data)
            merged_data = []

            for token in parsed_token_data:
                address = token['address'].lower()
                if address in token_dict:
                    db_token = token_dict[address]
                    merged_record = {
                        'name': db_token['name'],
                        'decimals': token['decimals'],
                        'mktcap': token['fdv_usd'],
                        'volume': token['volume_usd'],
                        'quantity': db_token['quantity'],
                        'buy_price': db_token['buy_price'],
                        'cur_price': token['price_usd']
                    }
                    merged_data.append(merged_record)

            return merged_data
        except Exception as e:
            logger.error(f"Unexpected error in merge_data")
            return []

    @staticmethod
    async def collect(config: Config, db_ops: DatabaseOperations) -> None:
        """Collect and process token data, then store it in the database."""
        try:
            if not config.token:
                logger.error(f"No tokens to process: {config.token}")
                return
            
            tokens: List[Dict[str, Any]] = []
            report: List[Dict[str, Any]] = []
            gas_price: float = 0.0

            timestamp = Util.get_local_time()
            latest = await db_ops.get_latest_entry()

            chain_addr = await Scheduler.merge_chain_addr(config)
            token_data = await Requests.get_token_data(config, chain_addr)
            merged_data = await Scheduler.merge_data(config, token_data)

            for entry in merged_data:
                try:
                    quantity = float(entry['quantity'])
                    entry['quantity'] = int(quantity) if quantity.is_integer() else quantity

                    entry['mktcap'] = int(float(entry['mktcap']))
                    entry['volume'] = int(float(entry['volume']))

                    buy_cost = round(float(entry['quantity']) * float(entry['buy_price']), 2)
                    if not buy_cost:
                        logger.warning(f"Invalid buy cost: {buy_cost}")
                        continue

                    entry['buy_cost'] = round(float(buy_cost), 2)

                    cur_cost = round(float(entry['quantity']) * float(entry['cur_price']), 2)
                    if not cur_cost:
                        logger.warning(f"Invalid current cost: {cur_cost}")
                        continue

                    entry['cur_cost'] = round(float(cur_cost), 2)

                    pnl_percent = Util.get_pnl(cur_cost, buy_cost)
                    if pnl_percent is None:
                        logger.warning(f"Invalid pnl percent: {pnl_percent}")
                        continue

                    entry['pnl_percent'] = round(float(pnl_percent), 2)
                    entry['pnl_delta'] = round(float(pnl_percent), 2)

                    if latest:
                        latest_entry = next((token for token in latest['tokens'] if token['name'] == entry['name']), None)
                    
                        if latest_entry:
                            latest_pnl_percent = latest_entry['pnl_percent']
                            entry['last_pnl_percent'] = latest_pnl_percent
                            pnl_delta = round(float(pnl_percent - latest_pnl_percent), 2)

                            if 'pnl_delta' in latest_entry:
                                accumulated_delta = round(float(latest_entry['pnl_delta'] + pnl_delta), 2)
                            else:
                                accumulated_delta = pnl_delta

                            if accumulated_delta > config.report_max_lim or accumulated_delta < config.report_min_lim:
                                entry_copy = entry.copy()
                                entry_copy['pnl_delta'] = round(float(accumulated_delta), 2)
                                report.append(entry_copy)
                                accumulated_delta = 0
                            
                            entry['pnl_delta'] = round(float(accumulated_delta), 2)

                            logger.info(
                                f"token: {entry['name']:<8} "
                                f"pnl: {pnl_percent:<8} "
                                f"last: {latest_pnl_percent:<8} "
                                f"delta: {entry['pnl_delta']:<8}"
                            )
                    else:
                        entry['pnl_delta'] = round(float(pnl_percent), 2)
                        report.append(entry)

                    tokens.append(entry)

                except KeyError as e:
                    logger.error(f"Missing key {e} in token data")
                except ValueError as e:
                    logger.error(f"Error processing token data: {e}")
                except Exception as e:
                    logger.error(f"[collect] Unexpected error: {e}")
            
            try:
                gas_price = await Requests.get_gas_price(config)
            except ValueError as e:
                logger.error(f"Error processing get gas price")
            except Exception as e:
                logger.error(f"Unexpected error")

            if len(tokens) > 0:
                entry = {
                    "datetime": timestamp,
                    "gas_price": gas_price,
                    "tokens": tokens
                }
                await db_ops.add_entry(entry)
                logger.info(f"Added {len(tokens)} tokens to database")

            if len(report) > 0:
                await Requests.send_report(config, {"report": report})

        except Exception as e:
            logger.error(f"Unexpected error in collect")