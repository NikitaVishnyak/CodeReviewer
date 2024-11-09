import os
import json
import logging
from typing import Optional, Dict

import aioredis

ONE_DAY = 60 * 60 * 24
ONE_MINUTE = 60

redis = aioredis.from_url(os.getenv('REDIS_URL'), decode_responses=True)


def generate_repo_cache_key(repo_url: str, level: str) -> str:
    """
    Generate key for further saving and retrieving the repository data cache.

    :param repo_url: The URL of the GitHub repository.
    :param level: The candidate level for which the code is being reviewed.
    :return: Formatted cache key.
    """
    return f'code:{repo_url}:{level}'


async def set_cached_github_repo(cache_key, data: Dict) -> None:
    """
    Cache the contents of a GitHub repository.

    :param cache_key: The key under which to store the cached repo data.
    :param data: The data to be cached, representing the repository contents.
    """
    logging.info(f"Setting cash: {cache_key}")
    await redis.set(cache_key, json.dumps(data), ex=ONE_DAY)


async def get_cached_github_repo(cache_key: str) -> Optional[Dict]:
    """
    Retrieve cached GitHub repository contents, if available.

    :param cache_key: The key under which the cached data is stored.
    :return: The cached data as a dictionary, or None if no cache is found.
    """
    cached_data = await redis.get(cache_key)
    if cached_data:
        logging.info("Using cached repository data.")
        return json.loads(cached_data)
    return None
