from discord.ext import commands
from discord.ext.commands import Context
from discord import Client, User, Embed, Colour
from classes.Player import Player
from classes.Game import Game
import classes.games.Battleships as bb
from main import get_prefix
from time import time
from re import search as re_search
import asyncio


class BattleshipsGameCog(commands.Cog):

    _player_to_game: dict[str, bb.BattleshipsGame] = {}  # allows player to use some commands outside the channel
    _channel_to_game: dict[str, bb.BattleshipsGame] = {}

    def __init__(self, client: Client):
        self.client: Client = client

    @commands.command(aliases=["Bchallenge", "BCHALLENGE", "bCHALLENGE"])
    async def bchallenge(self, ctx: Context, user: User):

        if ctx.guild is None:
            await ctx.reply("**Вы не можете бросить вызов кому-либо за пределами сервера**")
            return

        if ctx.author.id == user.id:
            await ctx.reply("**Вы не можете бросить вызов самому себе!**")
            return

        if ctx.channel.id in Game.occupied_channels:
            await ctx.reply("**Этот канал занят другой игрой!**")
            return

        if ctx.author.id in Player.occupied_players:
            await ctx.reply("**Вы уже участвуете в игре!**")
            return

        if user.id in Player.occupied_players:
            await ctx.reply(f"**{user.mention}  в другой игре!**")
            return

        embed = Embed(
            title="Battleships In-Game Commands📝",
            color=Colour.dark_blue()
        )

        prefix = get_prefix(self.client, ctx)

        embed.add_field(
            name="Внутриигровые команды ⚙️",
            value=f"**{prefix}bchallenge @user** (вызовите кого-нибудь на игру в боевые корабли)\n"
                  f"**{prefix}s pos** (стреляйте из своих пушек по посту) (Ex -> {prefix}s j6\n"
                  f"**{prefix}breroll** (меняйте свой флот до 3 раз)\n"
                  f"**{prefix}btimeout** (выиграйте, если ваш оппонент не играл более 120 секунд)\n"
                  f"**{prefix}myfleet** (просмотр вашего флота)\n"
                  f"**{prefix}bsurrender** (surrender the game)\n"
                  f"**{prefix}btie** (предложите ничью, если вы оба согласны, что игра заканчивается вничью)\n"
        )

        message = await ctx.send(
            content=f"**{ctx.author.mention} бросил вызов  {user.mention} к игре Battleships,"
                    f" согласится ли он?**",
            embed=embed
        )

        reactions = ["✅", "❌"]
        accepted = False

        for reaction in reactions:
            await message.add_reaction(reaction)

        def check(react, author):
            return author == user and str(react.emoji) in reactions

        while True:
            try:

                reaction, user = await self.client.wait_for("reaction_add", timeout=30, check=check)

                if str(reaction.emoji) == "✅":
                    accepted = True
                    break
                elif str(reaction.emoji) == "❌":
                    break

            except asyncio.TimeoutError:
                break

        if accepted:

            if ctx.channel.id in Game.occupied_channels:
                await ctx.reply("**Этот канал был занят до того, как вызов был принят!**")
                return

            if ctx.author.id in Player.occupied_players:
                await ctx.reply("**Вы присоединились к игре еще до того, как вызов был принят!**")
                return

            if user.id in Player.occupied_players:
                await ctx.reply(f"**{user.mention} присоединился к игре еще до того, как вызов был принят!**")
                return

            players = [ctx.author.id, user.id]

            game = bb.BattleshipsGame(players)

            Game.occupied_channels.append(ctx.channel.id)
            self._channel_to_game[str(ctx.channel.id)] = game

            for player in players:

                Player.occupied_players.append(player)
                self._player_to_game[str(player)] = game

                display = game.display(discord_id=player, view_opponent_fleet=False)

                player_discord = await self.client.fetch_user(player)

                await player_discord.send(
                    content=f"**Ваш флот!(доступно 3 повторных розыгрыша)**\n{display}"
                )

            await ctx.send(
                content=f"{ctx.author.mention}|{user.mention}\n"
                        f"**Игра начнется через 20 секунд, за это время вы можете сменить свой флот до 3 раз,"
                        f" если вы не удовлетворены своим текущим автопарком.**"
            )

            await asyncio.sleep(20)

            game.timer = time()
            game.ongoing = True

            await self.display(ctx, game)  # send the first message

        else:

            await ctx.reply(f"**{user.mention} отклонил/не ответил на вызов!**")

    @commands.command(aliases=["S", "shoot", "SHOOT", "Shoot", "sHOOT"])
    async def s(self, ctx: Context, pos: str):

        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:

                await ctx.reply("**Вы не являетесь частью этой игры с линкорами!**")
                return

        except KeyError:

            await ctx.reply("**На этом канале нет игры Battleships, запущенной на этом канале!**")
            return

        if not game.ongoing:

            await ctx.reply("**Игра еще не началась! Пожалуйста подождите**")
            return

        if ctx.author.id != game.current_round_player.discord_id:

            await ctx.reply("**Это не твоя очередь!**")
            return

        elif len(pos) != 2:

            await ctx.reply("**Неверные координаты (неправильный размер)\n"
                            "Example: a2**")
            return

        pos = pos.lower()

        pattern1 = "[a-j]+[0-9]"
        pattern2 = "[0-9]+[a-j]"

        if re_search(pattern1, pos):

            row = pos[0]
            column = int(pos[1])

        elif re_search(pattern2, pos):

            row = pos[1]
            column = int(pos[0])

        else:

            await ctx.reply("**Неверные координаты (неправильный формат)\n"
                            "Example: b6**")
            return

        hit, destroyed = game.shoot(row, column)

        if isinstance(hit, bb.Ship):

            if not destroyed:

                await ctx.reply(f"** Вы попали в корабль:boom:**")

            else:

                await ctx.reply(f"**Ты потопил {hit.name}({hit.size}):boom:**")

            if game.check_win():

                await ctx.send(f"**Адмирал:anchor: <@!{game.current_round_player.discord_id}>"
                               f" побежденный адмирал:anchor: <@!{game.next_player().discord_id}>!**")
                self.delete_game(ctx, game)

            else:

                game.next_round()

                await self.display(ctx, game)

        elif isinstance(hit, bb.Water):

            await ctx.reply(f"**Вы не попали!:radio_button:**")

            game.next_round()

            await self.display(ctx, game)

        elif isinstance(hit, bb.ExplodedShip):

            await ctx.reply(f"**Ты попал {pos} прежде чем попасть в корабль, пожалуйста, выстрелите в новый квадрат!**")

        else:

            await ctx.reply(f"**Ты попал {pos} прежде чем ни во что не попасть, пожалуйста, стреляйте в новый квадрат!**")

    @commands.command(aliases=["Breroll", "BREROLL", "bREROLL"])
    async def breroll(self, ctx: Context):

        try:

            game = self._player_to_game[str(ctx.author.id)]

        except KeyError:

            await ctx.reply("**Вы не участвовали ни в одной игре про линкоры!**")
            return

        response = game.change_fleet(ctx.author.id)

        if response == -2:
            await ctx.reply("**Игра продолжается, вы не можете изменить свой флот!**")
            return

        elif response == -1:
            await ctx.reply("**У вас закончились повторы!**")
            return

        display = game.display(ctx.author.id)

        await ctx.author.send(
            content=f"**Повторный запуск успешен, у вас есть {response} повторы влево!**\n{display}"
        )

    @commands.command(aliases=["Timeout", "TIMEOUT", "tIMEOUT"])
    async def btimeout(self, ctx: Context):

        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:

                await ctx.reply("**Вы не являетесь частью этой игры с линкорами!**")
                return

        except KeyError:

            await ctx.reply("**На этом канале нет игры Battleships, запущенной на этом канале!**")
            return

        if time() - game.timer > game.TIMEOUT:

            game.current_round_player = game.next_player()

            await ctx.send(f"**Адмирал:anchor: <@!{game.current_round_player.discord_id}> побежденный "
                           f"Адмирал:anchor: <@!{game.next_player().discord_id}> из-за "
                           f"бездействие последнего!**")

            self.delete_game(ctx, game)

        else:

            await ctx.reply(f"**<@!{game.next_player().discord_id}> имеет еще ~{game.TIMEOUT - (time() - game.timer)}"
                            f" секунды до начала игры!**")

    @commands.command(aliases=["Myfleet", "MYFLEET", "mYFLEET"])
    async def myfleet(self, ctx: Context):

        try:

            game = self._player_to_game[str(ctx.author.id)]

        except KeyError:

            await ctx.reply("**Вы не участвовали ни в одной игре про линкоры!**")
            return

        fleet_dis = game.display(discord_id=ctx.author.id, view_opponent_fleet=False)

        await ctx.author.send(
            content=f"**настала очередь игрока <@!{game.current_round_player.discord_id}>(Ваш флот:якорь:)**\n"
                    f"{fleet_dis}"
        )

    @commands.command(aliases=["Bsurrender", "BSURRENDER", "bSURRENDER"])
    async def bsurrender(self, ctx: Context):

        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:
                await ctx.reply("**Вы не являетесь частью этой игры с линкорами!**")
                return

        except KeyError:

            await ctx.reply("**На этом канале нет игры Battleships, запущенной на этом канале!**")
            return

        game.ongoing = False

        defeated = game.get_player_by_id(ctx.author.id)
        winner = [x for x in game.player_ids if x != defeated.discord_id][0]

        await ctx.send(f"**Адмирал:anchor:<@!{defeated.discord_id}> сдался адмиралу:anchor:<@!{winner}>**")

        self.delete_game(ctx, game)

    @commands.command(aliases=["Btie", "BTIE", "bTIE"])
    async def btie(self, ctx: Context):

        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:
                await ctx.reply("**Вы не являетесь частью этой игры с линкорами!**")
                return

        except KeyError:

            await ctx.reply("**На этом канале нет игры Battleships, запущенной на этом канале!**")
            return

        proposed_tie_player = game.get_player_by_id(ctx.author.id)
        other_player = [x for x in game.players if x.discord_id != ctx.author.id][0]

        proposed_tie_player.proposed_tie = True

        if proposed_tie_player.proposed_tie and other_player.proposed_tie:

            game.ongoing = False

            await ctx.send(f"**Адмирал:anchor:<@!{proposed_tie_player.discord_id}> "
                           f"и Адмирал:anchor:<@!{proposed_tie_player.discord_id}>"
                           f" согласился на ничью!**")

            self.delete_game(ctx, game)

        else:

            await ctx.send(f"**Адмирал:anchor:<@!{proposed_tie_player.discord_id}> "
                           f"предложил галстук адмиралу:anchor:<@!{other_player}>**")

    @classmethod
    async def display(cls, ctx: Context, game: bb.BattleshipsGame):

        fleet_dis = game.display()

        await ctx.send(
            content=f"**Настала очередь <@!{game.current_round_player.discord_id}>(Флот противника:crossed_swords:)**\n"
                    f"{fleet_dis}"
        )

    @classmethod
    def delete_game(cls, ctx: Context, game: bb.BattleshipsGame):

        Game.occupied_channels.remove(ctx.channel.id)
        del cls._channel_to_game[str(ctx.channel.id)]

        for player in game.players:

            Player.occupied_players.remove(player.discord_id)
            del cls._player_to_game[str(player.discord_id)]

        del game

    @bchallenge.error
    async def bchallenge_error(self, ctx: Context, error: Exception):

        prefix = get_prefix(self.client, ctx)

        if isinstance(error, commands.MissingRequiredArgument):

            await ctx.reply("**Вам нужно указать пользователя!\n"
                            f"Example: {prefix}bchallenge @user**")

        elif isinstance(error, commands.UserNotFound):

            await ctx.reply("**Пользователь не существует или не может быть найден!\n"
                            f"Example: {prefix}bchallenge @user**")

    @s.error
    async def s_error(self, ctx: Context, error: Exception):
        prefix = get_prefix(self.client, ctx)

        if isinstance(error, commands.MissingRequiredArgument):

            await ctx.reply("**Вам нужно указать координаты!\n"
                            f"Example: {prefix}s c8**")


def setup(client):
    client.add_cog(BattleshipsGameCog(client))
