import inspect
import sys
from collections import deque

from interactions import Extension, Intents, IntervalTrigger, Task, events, listen, __version__
from interactions.client.utils.cache import TTLCache

from statipy.client import StatipyClient
from statipy.db import CacheMetadata, GuildMetadata, Metadata, Stat


class Stats(Extension):
    def __init__(self, bot: StatipyClient):
        self.bot = bot
        self.bot_caches = {
            name.removesuffix("_cache"): cache
            for name, cache in inspect.getmembers(self.bot.cache, predicate=lambda x: isinstance(x, dict))
            if not name.startswith("__")
        }

    async def collect_stats(self):
        latency: deque
        if latency := self.bot.ws.latency:
            md = Metadata(client_id=self.bot.user.id, client_name=self.bot.client_name, name="latency", value=latency.pop())
            await Stat(meta=md).insert()

        for name, cache in self.bot_caches.items():
            md = CacheMetadata(
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                name="cache",
                cache_name=name,
                value=len(cache),
            )
            await Stat(meta=md).insert()

            soft_md = CacheMetadata(
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                name="cache_soft_limit",
                cache_name=name,
                value="inf",
            )
            hard_md = CacheMetadata(
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                name="cache_hard_limit",
                cache_name=name,
                value="inf",
            )

            if isinstance(cache, TTLCache):
                soft_md.value = cache.soft_limit
                hard_md.value = cache.hard_limit

            await Stat(meta=soft_md).insert()
            await Stat(meta=hard_md).insert()

    @listen(delay_until_ready=True)
    async def on_ready(self) -> None:
        major, minor, patch, *_ = sys.version_info

        await Stat(
            meta=Metadata(
                name="library_version", client_id=self.bot.user.id, client_name=self.bot.client_name, value=__version__
            )
        ).insert()

        await Stat(
            meta=Metadata(
                name="python_version",
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                value=f"{major}.{minor}.{patch}",
            )
        ).insert()

        for guild in self.bot.guilds:
            member_count = guild.member_count
            if Intents.GUILD_MEMBERS in self.bot.intents:
                member_count = len(guild._member_ids)

            channels_md = GuildMetadata(
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                name="channel_count",
                value=len(guild._channel_ids),
                guild_id=guild.id,
                guild_name=guild.name,
            )

            members_md = GuildMetadata(
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                name="member_count",
                value=member_count,
                guild_id=guild.id,
                guild_name=guild.name,
            )

            await Stat(meta=channels_md).insert()
            await Stat(meta=members_md).insert()

            stats_task = Task(self.collect_stats, IntervalTrigger(seconds=5))
            stats_task.start()

    @listen(delay_until_ready=True)
    async def on_message_create(self, event: events.MessageCreate):
        guild_id = None
        guild_name = None
        dm = True
        if event.message.guild:
            guild_id = event.message.guild.id
            guild_name = event.message.guild.name
            dm = False

        md = GuildMetadata(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="message_received",
            value=1,
            guild_id=guild_id,
            guild_name=guild_name,
            dm=dm,
        )
        await Stat(meta=md).insert()

    @listen(delay_until_ready=True)
    async def on_guild_join(self, _):
        md = Metadata(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="total_guilds",
            value=len(self.bot.guilds),
        )
        await Stat(meta=md).insert()

    @listen(delay_until_ready=True)
    async def on_guild_left(self, _):
        md = Metadata(
            client_id=self.bot.user.id, client_name=self.bot.client_name, name="guild_event", value=len(self.bot.guilds)
        )
        await Stat(meta=md).insert()

    @listen(delay_until_ready=True)
    async def on_member_add(self, event: events.MemberAdd):
        member_count = event.guild.member_count
        if Intents.GUILD_MEMBERS in self.bot.intents:
            member_count = len(event.guild._member_ids)
        md = GuildMetadata(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="member_count",
            value=member_count,
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )
        await Stat(meta=md).insert()

    @listen(delay_until_ready=True)
    async def on_member_remove(self, event: events.MemberRemove):
        member_count = event.guild.member_count
        if Intents.GUILD_MEMBERS in self.bot.intents:
            member_count = len(event.guild._member_ids)
        md = GuildMetadata(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="member_count",
            value=member_count,
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )
        await Stat(meta=md).insert()

    @listen(delay_until_ready=True)
    async def on_channel_create(self, event: events.ChannelCreate):
        md = GuildMetadata(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="channel_count",
            value=len(event.guild._channel_ids),
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )
        await Stat(meta=md).insert()

    @listen(delay_until_ready=True)
    async def on_channel_delete(self, event: events.ChannelDelete):
        md = GuildMetadata(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="channel_count",
            value=len(event.guild._channel_ids),
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )
        await Stat(meta=md).insert()


def setup(bot: StatipyClient):
    if not isinstance(bot, StatipyClient):
        raise ValueError("This extension can only be used with a StatipyClient")
    Stats(bot)
