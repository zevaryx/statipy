from datetime import datetime, timezone, timedelta
from typing import Optional

from beanie import Document, Granularity, TimeSeriesConfig, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field


def get_now() -> datetime:
    """Return now with UTC timezone"""
    return datetime.now(tz=timezone.utc)


async def init_db(
    username: str,
    password: str,
    port: int = 27017,
    host: str = None,
    hosts: list[str] = None,
    replicaset: str = None,
):
    if not replicaset:
        client = AsyncIOMotorClient(username=username, password=password, host=host, port=port)
    else:
        client = AsyncIOMotorClient(hosts, username=username, password=password, replicaset=replicaset)
    await init_beanie(database=client["statipy"], document_models=[Stat, StaticStat])


class StaticStat(Document):
    name: str
    client_id: int
    client_name: str
    value: float | int | str | timedelta
    guild_id: Optional[int]
    guild_name: Optional[str]
    dm: bool = False


class Metadata(BaseModel):
    client_id: int
    client_name: str
    value: float | int | str | timedelta


class CacheMetadata(Metadata):
    cache_name: str


class GuildMetadata(Metadata):
    guild_id: Optional[int]
    guild_name: Optional[str]
    dm: bool = False


class ChannelMetadata(GuildMetadata):
    channel_id: Optional[int]
    channel_name: Optional[str]


class SlashMetadata(GuildMetadata):
    base_name: Optional[str]
    group_name: Optional[str]
    command_name: Optional[str]
    command_id: int


class Stat(Document):
    name: str
    timestamp: datetime = Field(default_factory=get_now)
    meta: Metadata

    class Settings:
        timeseries = TimeSeriesConfig(time_field="timestamp", meta_field="meta", granularity=Granularity.seconds)
