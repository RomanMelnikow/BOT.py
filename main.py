import aiohttp
from discord.ext.commands.context import Context
from discord.ext.commands import has_permissions
from discord.ext import commands
from os import listdir
from discord import Guild
import json
import config




def get_prefix(bot_obj, message: Context) -> str:

    try:
        with open("bot/prefixes.json", 'r') as f:
            prefixes = json.load(f)

        return prefixes[str(message.guild.id)]

    except AttributeError:
        return '-'

    except KeyError:
        return '-'


client = commands.Bot(command_prefix=get_prefix)

for filename in listdir("cogs"):  # load all cogs/extensions

    if filename.endswith(".py"):

        client.load_extension(f"cogs.{filename[:-3]}")


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_command_error(ctx: Context, error: Exception):
    print('ignor')


@client.event
async def on_guild_remove(guild: Guild):

    with open("bot/prefixes.json", 'r') as f:
        prefixes = json.load(f)

    try:
        prefixes.pop(str(guild.id))

        with open("bot/prefixes.json", 'w') as f:
            json.dump(prefixes, f, indent=4)

    except KeyError:
        pass


@client.command(aliases=["PREFIX", "Prefix", "pREFIX"])
@has_permissions(administrator=True)
async def prefix(ctx: Context, new_prefix: str):

    if ctx.guild is None:

        await ctx.reply("**Вы не можете изменить префикс за пределами сервера!**")
        return

    if len(new_prefix) > 4:

        await ctx.reply("**Длина префикса не может превышать 4 символов!**")
        return

    with open("bot/prefixes.json", 'r') as f:
        prefixes = json.load(f)

    prefixes[str(ctx.guild.id)] = new_prefix

    with open("bot/prefixes.json", 'w') as f:
        json.dump(prefixes, f, indent=4)

    await ctx.send(f"**Префикс изменен на {new_prefix}**")


@prefix.error
async def prefix_error(ctx: Context, error: Exception):

    if isinstance(error, commands.MissingRequiredArgument):

        await ctx.reply("**Неправильное использование!\n"
                        f"Example: {get_prefix(client, ctx)}prefix .**")

    elif isinstance(error, commands.MissingPermissions):

        await ctx.reply("**У вас нет разрешения на изменение префикса сервера!**")

client.run(config.token)