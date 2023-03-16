import inspect
import sys

from beanie.operators import Inc, Set
from interactions import Extension, Intents, IntervalTrigger, Task, events, listen, __version__
from interactions.client.utils.cache import TTLCache

from statipy.client import StatipyClient
from statipy.db import CacheMetadata, GuildMetadata, Metadata, Stat, StaticStat

class Stats(Extension):
    def __init__(self, bot: StatipyClient, include_cache: bool = False):
        self.bot = bot
        self.include_cache = include_cache
        if self.include_cache:
            self.bot.logger.warn("Statipy include_cache is true! This will insert very many documents into your database")
            self.bot_caches = {
                c[0]: getattr(bot.cache, c[0])
                for c in inspect.getmembers(bot.cache, predicate=lambda x: isinstance(x, dict))
                if not c[0].startswith("__")
            }
            self.bot_caches["endpoints"] = self.bot.http._endpoints
            self.bot_caches["rate_limits"] = self.bot.http.ratelimit_locks

    async def collect_stats(self):
        if latency := self.bot.ws.latency:
            md = Metadata(client_id=self.bot.user.id, client_name=self.bot.client_name, name="latency", value=latency)
            await Stat(meta=md).insert()

        if self.include_cache:
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

        await StaticStat.find_one(
            StaticStat.name == "library_version", StaticStat.client_id == self.bot.user.id
        ).upsert(
            Set(
                {
                    StaticStat.client_name: self.bot.client_name,
                    StaticStat.value: __version__,
                }
            ),
            on_insert=StaticStat(
                name="library_version",
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                value=__version__,
            ),
        )
        await StaticStat.find_one(StaticStat.name == "python_version", StaticStat.client_id == self.bot.user.id).upsert(
            Set(
                {
                    StaticStat.client_name: self.bot.client_name,
                    StaticStat.value: f"{major}.{minor}.{patch}",
                }
            ),
            on_insert=StaticStat(
                name="python_version",
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                value=f"{major}.{minor}.{patch}",
            ),
        )

        await StaticStat.find_one(StaticStat.name == "total_guilds", StaticStat.client_id == self.bot.user.id).upsert(
            Set(
                {
                    StaticStat.client_name: self.bot.client_name,
                    StaticStat.value: len(self.bot.guilds),
                }
            ),
            on_insert=StaticStat(
                name="total_guilds",
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                value=len(self.bot.guilds),
            ),
        )

        for guild in self.bot.guilds:
            await guild.http_chunk()
            member_count = guild.member_count
            if Intents.GUILD_MEMBERS in self.bot.intents:
                member_count = len(guild._member_ids)

            channels = StaticStat(
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                name="channel_count",
                value=len(guild._channel_ids),
                guild_id=guild.id,
                guild_name=guild.name,
            )

            members = StaticStat(
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                name="member_count",
                value=member_count,
                guild_id=guild.id,
                guild_name=guild.name,
            )

            await StaticStat.find_one(
                StaticStat.name == "channel_count",
                StaticStat.client_id == self.bot.user.id,
                StaticStat.guild_id == guild.id,
            ).upsert(
                Set(
                    {
                        StaticStat.client_name: self.bot.client_name,
                        StaticStat.value: len(guild._channel_ids),
                        StaticStat.guild_name: guild.name,
                    }
                ),
                on_insert=channels,
            )

            await StaticStat.find_one(
                StaticStat.name == "member_count",
                StaticStat.client_id == self.bot.user.id,
                StaticStat.guild_id == guild.id,
            ).upsert(
                Set(
                    {
                        StaticStat.client_name: self.bot.client_name,
                        StaticStat.value: member_count,
                        StaticStat.guild_name: guild.name,
                    }
                ),
                on_insert=members,
            )

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
        if not self.bot.is_ready:
            return
        md = Metadata(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="guild_event",
            value=1,
        )
        await Stat(meta=md).insert()

        await StaticStat.find_one(StaticStat.name == "total_guilds", StaticStat.client_id == self.bot.user.id).upsert(
            Set(
                {
                    StaticStat.client_name: self.bot.client_name,
                    StaticStat.value: len(self.bot.guilds),
                }
            ),
            on_insert=StaticStat(
                name="total_guilds",
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                value=len(self.bot.guilds),
            ),
        )

    @listen(delay_until_ready=True)
    async def on_guild_left(self, _):
        if not self.bot.is_ready:
            return
        md = Metadata(client_id=self.bot.user.id, client_name=self.bot.client_name, name="guild_event", value=-1)
        await Stat(meta=md).insert()

        await StaticStat.find_one(StaticStat.name == "total_guilds", StaticStat.client_id == self.bot.user.id).upsert(
            Set(
                {
                    StaticStat.client_name: self.bot.client_name,
                    StaticStat.value: len(self.bot.guilds),
                }
            ),
            on_insert=StaticStat(
                name="total_guilds",
                client_id=self.bot.user.id,
                client_name=self.bot.client_name,
                value=len(self.bot.guilds),
            ),
        )

    @listen(delay_until_ready=True)
    async def on_member_add(self, event: events.MemberAdd):
        member_count = event.guild.member_count
        if Intents.GUILD_MEMBERS in self.bot.intents:
            member_count = len(event.guild._member_ids)

        md = GuildMetadata(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="member_event",
            value=1,
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )
        await Stat(meta=md).insert()

        members = StaticStat(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="member_count",
            value=member_count,
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )

        await StaticStat.find_one(
            StaticStat.name == "member_count",
            StaticStat.client_id == self.bot.user.id,
            StaticStat.guild_id == event.guild.id,
        ).upsert(
            Set(
                {
                    StaticStat.client_name: self.bot.client_name,
                    StaticStat.guild_name: event.guild.name,
                }
            ),
            Inc({StaticStat.value: 1}),
            on_insert=members,
        )

    @listen(delay_until_ready=True)
    async def on_member_remove(self, event: events.MemberRemove):
        member_count = event.guild.member_count
        if Intents.GUILD_MEMBERS in self.bot.intents:
            member_count = len(event.guild._member_ids)

        md = GuildMetadata(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="member_event",
            value=-1,
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )
        await Stat(meta=md).insert()

        members = StaticStat(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="member_count",
            value=member_count,
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )

        await StaticStat.find_one(
            StaticStat.name == "member_count",
            StaticStat.client_id == self.bot.user.id,
            StaticStat.guild_id == event.guild.id,
        ).upsert(
            Set(
                {
                    StaticStat.client_name: self.bot.client_name,
                    StaticStat.guild_name: event.guild.name,
                }
            ),
            Inc({StaticStat.value: -1}),
            on_insert=members,
        )

    @listen(delay_until_ready=True)
    async def on_channel_create(self, event: events.ChannelCreate):
        md = GuildMetadata(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="channel_event",
            value=1,
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )
        await Stat(meta=md).insert()

        channels = StaticStat(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="channel_count",
            value=len(event.guild._channel_ids),
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )

        await StaticStat.find_one(
            StaticStat.name == "channel_count",
            StaticStat.client_id == self.bot.user.id,
            StaticStat.guild_id == event.guild.id,
        ).upsert(
            Set(
                {
                    StaticStat.client_name: self.bot.client_name,
                    StaticStat.value: len(event.guild._channel_ids),
                    StaticStat.guild_name: event.guild.name,
                }
            ),
            on_insert=channels,
        )

    @listen(delay_until_ready=True)
    async def on_channel_delete(self, event: events.ChannelDelete):
        md = GuildMetadata(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="channel_event",
            value=-1,
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )
        await Stat(meta=md).insert()

        channels = StaticStat(
            client_id=self.bot.user.id,
            client_name=self.bot.client_name,
            name="channel_count",
            value=len(event.guild._channel_ids),
            guild_id=event.guild.id,
            guild_name=event.guild.name,
        )

        await StaticStat.find_one(
            StaticStat.name == "channel_count",
            StaticStat.client_id == self.bot.user.id,
            StaticStat.guild_id == event.guild.id,
        ).upsert(
            Set(
                {
                    StaticStat.client_name: self.bot.client_name,
                    StaticStat.value: len(event.guild._channel_ids),
                    StaticStat.guild_name: event.guild.name,
                }
            ),
            on_insert=channels,
        )


def setup(bot: StatipyClient):
    if not isinstance(bot, StatipyClient):
        raise ValueError("This extension can only be used with a StatipyClient")
    Stats(bot)
