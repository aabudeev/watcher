# -*- coding: utf-8 -*-

import time
import logging
import inspect
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Union

class FunctionNameFilter(logging.Filter):
    """
    A logging filter to add the name of the function where the logging call was made.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add the function name to the log record.

        Args:
            record (logging.LogRecord): The log record to modify.

        Returns:
            bool: Always returns True to ensure the log record is not filtered out.
        """

        stack = inspect.stack()
        for frame_info in stack[2:]:
            module = inspect.getmodule(frame_info.frame)
            if module and not module.__name__.startswith('logging'):
                record.funcName = frame_info.function
                break
        else:
            record.funcName = 'main'
        return True

def setup_logging(log_file: str, max_bytes: int = 1 * 1024 * 1024, backup_count: int = 5):
    """
    Set up logging with rotating file handler and console handler.

    Args:
        log_file (str): The name of the log file.
        max_bytes (int): The maximum size of the log file in bytes before it gets rotated.
        backup_count (int): The number of backup files to keep.

    Returns:
        logging.Logger: Configured logger.
    """

    logger = logging.getLogger()
    if not logger.handlers:
        log_format = "[%(asctime)s][%(levelname)s][%(funcName)s] - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"

        file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)   # DEBUG, INFO, WARNING, ERROR, CRITICAL
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.addFilter(FunctionNameFilter())
        
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('telegram').setLevel(logging.WARNING)

    return logger

logger = setup_logging("watcher.log")

def get_local_time() -> int:
    """
    Get the current local time in seconds since the Epoch.

    Returns:
        int: The current local time in seconds since the Epoch.
    """

    try:
        local_time = int(time.mktime(time.localtime(time.time())))
        return local_time
    except Exception as e:
        logger.error(f"Unexpected error in get_local_time: {e}")
        return 0
    
def get_socks5_url(config: Any) -> str:
    """
    Generate the SOCKS5 URL from the configuration details.

    Args:
        config (Any): The configuration object containing SOCKS5 proxy details.

    Returns:
        str: The generated SOCKS5 URL.
    """

    try:
        socks5_url = f"socks5://{config.socks5_username}:{config.socks5_password}@{config.socks5_ip}:{config.socks5_port}"
        return socks5_url
    except AttributeError as e:
        logger.error(f"AttributeError in get_socks5_url: {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error in get_socks5_url: {e}")
        return ""

def get_pnl(cur_cost: float, buy_cost: float) -> float:
    """
    Calculate the profit and loss (PnL) percentage.

    Args:
        cur_cost (float): The current cost of the asset.
        buy_cost (float): The buying cost of the asset.

    Returns:
        float: The PnL percentage.
    """

    try:
        pnl_percent = round(((cur_cost * 100) / buy_cost), 2)

        if pnl_percent < 100:
            pnl_percent = round((pnl_percent - 100), 2)

        elif pnl_percent < 0:
            pnl_percent = round((abs(pnl_percent) - 100), 2)

        return pnl_percent
    except Exception as e:
        logger.error(f"Unexpected error in get_pnl: {e}")
        return 0.0

def simplify(data: Union[int, float, str], format: int = 0) -> str:
    """
    Simplify large numbers into a more readable string format.

    Args:
        data (Union[int, float, str]): The number to simplify.
        format (int): The format type (0 for default formatting, 1 for scientific-like notation).

    Returns:
        str: The simplified number as a string.
    """

    subscript_map = { 1: '₁', 2: '₂', 3: '₃', 4: '₄', 5:  '₅', 6: '₆', 7: '₇', 8: '₈', 9: '₉', 10: '₁₀' }

    try:
        if isinstance(data, str):
            data = float(data)

        if format == 0:
            suffixes = ["", "K", "M", "B", "T"]
            magnitude = 0
            while abs(data) >= 1000 and magnitude < len(suffixes) - 1:
                magnitude += 1
                data /= 1000.0
            return f"{data:.2f}".rstrip('0').rstrip('.') + suffixes[magnitude]

        elif format == 1:
            data_str = f"{data:.20f}"
            data_str = data_str.rstrip('0')

            if '.' in data_str:
                integer_part, fractional_part = data_str.split('.')
            else:
                integer_part, fractional_part = data_str, ""

            if integer_part == '0':
                leading_zeros = len(fractional_part) - len(fractional_part.lstrip('0'))
                if leading_zeros > 0:
                    subscript = subscript_map.get(leading_zeros, f"_{leading_zeros}")
                    fractional_part = fractional_part.lstrip('0')[:4]
                    return f"0.0{subscript}{fractional_part}"
                else:
                    fractional_part = fractional_part[:4]
                    return f"0.{fractional_part}"
            else:
                fractional_part = fractional_part[:4]
                return f"{integer_part}.{fractional_part}"

        return str(data)
    except Exception as e:
        logger.error(f"Unexpected error in simplify: {e}")
        return str(data)

def get_worth(config: Any, entry: Any) -> Dict[str, Any]:
    """
    Calculate the total purchased value, current worth, and profit/loss (PNL).

    Args:
        config (Any): Configuration object containing token purchase details.
        entry (Any): The latest database entry containing current token costs.

    Returns:
        Dict[str, int]: A dictionary containing the total purchased value, current worth, and PNL.
    """

    try:
        purchased = 0
        current_worth = 0

        tokens = config.token
        if tokens:
            for item in tokens:
                buy_price = float(item['buy_price'])
                quantity = float(item['quantity'])
                purchased += buy_price * quantity

        latest = entry.get('tokens', [])
        if latest:
            for item in latest:
                cur_cost = float(item['cur_cost'])
                current_worth += cur_cost

        specific = 10000 # Correcting value specific for your deposit
        correcting_value = specific - purchased
        purchased += correcting_value

        pnl = get_pnl(current_worth, purchased)
        
        worth = {
            "purchased": int(purchased),
            "worth": int(current_worth),
            "pnl": int(pnl)
        }

        return worth
    except Exception as e:
        logger.error(f"Unexpected error in get_worth: {e}")

def format_datetime_msk(timestamp: int) -> str:
    """
    Convert a timestamp to a formatted datetime string in MSK (UTC+3).

    Args:
        timestamp (int): The timestamp to convert.

    Returns:
        str: The formatted datetime string in MSK.
    """

    try:
        dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        dt_msk = dt_utc + timedelta(hours=3)
        return dt_msk.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.error(f"Unexpected error in format_datetime_msk: {e}")
        return 0

def format_msg_inform(config: Any, entry: Dict[str, Any]) -> str:
    """
    Format a message with token information.

    Args:
        config (Any): Configuration object containing report limits.
        entry (Dict[str, Any]): Entry data containing token details.

    Returns:
        str: Formatted message with token information.
    """

    try:
        token = entry.get('name', "")
        mktcap = simplify(entry.get('mktcap', 0))
        volume = simplify(entry.get('volume', 0))
        cur_price = simplify(entry.get('cur_price', 0), format=1)
        quantity = simplify(entry.get('quantity', 0))
        buy_cost = entry.get('buy_cost', 0)
        cur_cost = entry.get('cur_cost', 0)
        pnl_percent = entry.get('pnl_percent', 0)
        pnl_delta = entry.get('pnl_delta', 0)
        char = '🔴' if pnl_percent < 0 else '🟢' if pnl_percent > 0 else '🔄'
        range = '⬆️' if float(pnl_delta) > float(config.report_max_lim) else '⬇️' if float(pnl_delta) < float(config.report_min_lim) else '🔄'

        msg = (
            f"<code>▪️ Token:    </code>#{token}\n"
            f"<code>▪️ Mktcap:   {mktcap}</code>\n"
            f"<code>▪️ Volume:   {volume}</code>\n\n"
            f"<code>▪️ Quantity: {quantity}</code>\n"
            f"<code>▪️ Buy:      {buy_cost}$</code>\n\n"
            f"<code>{range} {pnl_delta}%</code>\n"
            f"<code>▪️ Price:    {cur_price}</code>\n"
            f"<code>▪️ Cost:     {cur_cost}$</code>\n"
            f"<code>{char} Pnl:      {pnl_percent}%</code>\n"
        )
        
        return msg
    except Exception as e:
        logger.error(f"Unexpected error in format_msg_inform: {e}")
        return ''
    
def format_msg_report(worth: Dict[str, Any], entry: Dict[str, Any]) -> str:
    """
    Format a message report with financial worth and entry data.

    Args:
        worth (Dict[str, Any]): Dictionary containing financial worth details.
        entry (Dict[str, Any]): Dictionary containing entry details.

    Returns:
        str: Formatted message report.
    """

    try:
        datetime_value = entry.get('datetime', '')
        if isinstance(datetime_value, int):
            datetime_value = format_datetime_msk(datetime_value)

        gas = entry.get('gas_price', '')

        purchased = worth['purchased']
        current_worth = worth['worth']
        pnl = worth['pnl']
        char = '🔴' if pnl < 0 else '🟢'

        header = (
            f"<code>▪️ date: {datetime_value}</code>\n"
            f"<code>▪️ gas price:  {gas}$</code>\n\n"
            f"<code>▪️ Purchased:  {purchased}$</code>\n"
            f"<code>{char} Worth:      {current_worth}$</code>\n"
            f"<code>{char} PNL:        {pnl}%</code>\n\n"
        )

        body: List[str] = []
        latest = entry.get('tokens', [])
        if latest:
            for item in latest:
                name = f"{item['name']:<8}"
                pnl_percent = f"{int(item['pnl_percent'])}%".rjust(8)
                cur_cost = f"{int(item['cur_cost'])}$".rjust(8)
                char = '🔴' if item['pnl_percent'] < 0 else '🟢'
                body.append(f"<code>{char} {name} {pnl_percent} {cur_cost}</code>\n")
        
        return header + ''.join(body)
    except Exception as e:
        logger.error(f"Unexpected error in format_msg_report: {e}")
        return ''