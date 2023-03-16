from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Granularity, TimeSeriesConfig, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field


def get_now() -> datetime:
    """Return now with UTC timezone"""
    return datetime.now(tz=timezone.utc)


async def init_db(host: str = "localhost", port: int = 27017, user: str = None, password: str = None):
    client = AsyncIOMotorClient(username=user, password=password, host=host, port=port)
    await init_beanie(database=client["statipy"], document_models=[Stat])


class Metadata(BaseModel):
    client_id: int
    client_name: str
    name: str
    value: int | str


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
    command_name: str
    command_id: int


class Stat(Document):
    timestamp: datetime = Field(default=get_now)
    meta: Metadata

    class Settings:
        timeseries = TimeSeriesConfig(time_field="timestamp", meta_field="meta", granularity=Granularity.seconds)
