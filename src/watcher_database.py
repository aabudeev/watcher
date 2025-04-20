# -*- coding: utf-8 -*-

import logging
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class DatabaseOperations:
    """
    A class to handle database operations for storing and retrieving data.
    """

    def __init__(self, db: AsyncIOMotorClient) -> None:
        """
        Initialize the database operations with the given database connection.
        
        Args:
            db (AsyncIOMotorClient): The MongoDB client instance.
        """
        self.db = db
        self.collection = db['data']

    async def add_entry(self, entry: Dict[str, Any]) -> None:
        """
        Add a new entry to the database.
        Args:
            entry (Dict[str, Any]): The entry data to be added to the database.
        """
        await self.collection.insert_one(entry)

    async def get_latest_entry(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the latest entry from the database.
        Returns:
            Optional[Dict[str, Any]]: The latest entry data, or None if no entries are found.
        """
        return await self.collection.find_one(sort=[("datetime", -1)])
    
    async def get_latest_gas_price(self) -> Optional[float]:
        """
        Retrieve the gas price from the latest entry in the database.
        Returns:
            Optional[float]: The gas price from the latest entry, or None if no entries are found.
        """
        latest = await self.get_latest_entry()
        if latest:
            return latest.get('gas_price')
        return None
    
    async def get_latest_worth(self) -> int:
        """
        Calculate the total current cost of all tokens from the latest entry.
        Returns:
            float: The total current cost of all tokens.
        """
        latest = await self.get_latest_entry()
        latest_entry = latest['tokens']

        total_cur_cost = 0
        
        if latest_entry:
            for token in latest_entry:
                cur_cost = float(token.get("cur_cost", 0))
                total_cur_cost += cur_cost
        
        return int(total_cur_cost)