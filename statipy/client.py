import time
from typing import Any

from interactions import BaseCommand, BaseContext, Client, SlashContext, listen
from interactions.ext.prefixed_commands import PrefixedContext

from statipy.db import SlashMetadata, Metadata, Stat, init_db


class StatipyClient(Client):
    @property
    def client_name(self) -> str:
        if self.user.username:
            return self.user.username + "#" + str(self.user.discriminator)
        else:
            return str(self.user.id)

    async def syncronise_interactions(self) -> None:
        st = time.time()
        await super().synchronise_interactions()
        et = time.time()

        meta = Metadata(
            client_id=self.user.id,
            client_name=self.client_name,
            name="sync_time",
            value=et - st,
        )
        stat = Stat(meta=meta)

        await stat.insert()

    async def _run_slash_command(self, command: BaseCommand, ctx: BaseContext) -> Any:
        guild_id = None
        guild_name = None
        dm = True
        if ctx.guild:
            guild_id = ctx.guild.id
            guild_name = ctx.guild.name
            dm = False
        try:
            md = SlashMetadata(
                client_id=self.user.id,
                client_name=self.client_name,
                base_name=command.name.default,
                command_id=ctx.command_id,
                guild_id=guild_id,
                guild_name=guild_name,
                name="command_run",
                dm=dm,
                value=1,
            )
            if isinstance(ctx, SlashContext):
                md.group_name = command.group_name.default
                md.command_name = command.sub_cmd_name.default

            stat = Stat(meta=md)
            await stat.insert()
        except Exception:
            self.logger.error("Error saving statistics", exc_info=True)
        return await command(ctx, **ctx.kwargs)

    async def on_command_error(self, ctx: BaseContext, error: Exception, *args, **kwargs) -> None:
        if not isinstance(ctx, PrefixedContext):
            command = ctx.command
            guild_id = None
            guild_name = None
            dm = True
            if ctx.guild:
                guild_id = ctx.guild.id
                guild_name = ctx.guild.name
                dm = False

            md = SlashMetadata(
                client_id=self.user.id,
                client_name=self.client_name,
                base_name=command.name.default,
                command_id=ctx.command_id,
                guild_id=guild_id,
                guild_name=guild_name,
                name="command_error",
                dm=dm,
                value=1,
            )
            if isinstance(ctx, SlashContext):
                md.group_name = command.group_name.default
                md.command_name = command.sub_cmd_name.default

            stat = Stat(meta=md)
            await stat.insert()
