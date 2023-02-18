from discord.ext import commands
from discord.ext.commands import Context
from discord import Client, User, Embed, Colour
import classes.games.TicTacToe as tic
from classes.Game import Game
from classes.Player import Player
from main import get_prefix
from time import time
import asyncio


class TicTacToeGameCog(commands.Cog):

    _channel_to_game: dict[str, tic.TicTacToeGame] = {}

    def __init__(self, client: Client):
        self.client: Client = client

    @commands.command()
    async def tchallenge(self, ctx: Context, user: User):
        await ctx.message.delete()

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
            await ctx.reply(f"**{user.mention} это в другой игре!**")
            return

        embed = Embed(
            title="Команды в игре в крестики-нолики 📝 Команды в игре в крестики-нолики 📝",
            color=Colour.red()
        )

        prefix = get_prefix(self.client, ctx)

        embed.add_field(
            name="In-Game Commands ⚙️",
            value=f"**{prefix}tchallenge @user** (вызовите пользователя на игру в крестики-нолики)\n"
                  f"**{prefix}p pos** (поместите свой символ в pos, число от 0 до 8\n"
                  f"**{prefix}tsurrender** (проиграйте игру)\n"
                  f"**{prefix}ttimeout** (выиграйте, если соперник не играл в течение 100 секунд)\n"
                  f"**{prefix}ttie** (предложите своему оппоненту ничью)\n"
        )

        message = await ctx.send(
            content=f"**{ctx.author.mention} бросил вызов {user.mention} к игре в крестики-нолики,"
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

            game = tic.TicTacToeGame(players)

            Game.occupied_channels.append(ctx.channel.id)
            self._channel_to_game[str(ctx.channel.id)] = game

            for player in players:

                Player.occupied_players.append(player)

            await ctx.send(
                content=f"**{ctx.author.mention} ⚔️ {user.mention}\n"
                        f"-------------------------\n" 
                        f"{game.get_player_by_id(ctx.author.id).emoji}{ctx.author.mention}\n"
                        f"{game.get_player_by_id(user.id).emoji}{user.mention}**"
            )

            await asyncio.sleep(1)

            game.timer = time()
            game.ongoing = True

            await self.display(ctx, game)  # send the first message

        else:

            await ctx.reply(f"**{user.mention} отклонил/не ответил на вызов!**")

    @commands.command()
    async def p(self, ctx: Context, pos: int):

        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:

                await ctx.reply("**Вы не являетесь частью этой игры в крестики-нолики!**")
                return

        except KeyError:

            await ctx.reply("**На этом канале нет игры в крестики-нолики!**")
            return

        if pos not in range(0, 9):

            await ctx.reply("**Число должно быть в диапазоне 0-8!**")
            return

        if game.current_round_player.discord_id != ctx.author.id:

            await ctx.reply("**Это не твоя очередь!**")
            return

        success = game.board.place(game.current_round_player.symbol, pos)

        if success:

            if game.board.check_win(game.current_round_player.symbol):

                winner = game.current_round_player
                loser = game.next_player()

                await ctx.send(f"**{winner.emoji}<@!{winner.discord_id}> побежденный "
                               f"{loser.emoji}<@!{loser.discord_id}> в игре в крестики-нолики!**")


                self.delete_game(ctx, game)

            else:

                game.next_round()
                await self.display(ctx, game)

        else:

            await ctx.reply(f"**Место #{pos} занято!**")

    @commands.command()
    async def tsurrender(self, ctx: Context):

        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:

                await ctx.reply("**Вы не являетесь частью этой игры в крестики-нолики!**")
                return

        except KeyError:

            await ctx.reply("**На этом канале нет игры в крестики-нолики!**")
            return

        loser = game.get_player_by_id(ctx.author.id)
        winner = [x for x in game.players if x.discord_id != loser.discord_id][0]

        await ctx.send(f"**{loser.emoji}<@!{loser.discord_id}> сдался на {winner.emoji}<@!{winner.discord_id}>!**")

        self.delete_game(ctx, game)

    @commands.command()
    async def ttie(self, ctx: Context):

        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:

                await ctx.reply("**Вы не являетесь частью этой игры в крестики-нолики!**")
                return

        except KeyError:

            await ctx.reply("**На этом канале нет игры в крестики-нолики!**")
            return

        thisplayer = game.get_player_by_id(ctx.author.id)
        otherplayer = [x for x in game.players if x.discord_id != thisplayer.discord_id][0]

        thisplayer.proposed_tie = True

        if thisplayer.proposed_tie and otherplayer.proposed_tie:

            await ctx.send(
                f"**{thisplayer.emoji}<@!{thisplayer.discord_id}> и {otherplayer.emoji}<@!{otherplayer.discord_id}>"
                f"согласился на ничью!**"
            )

            self.delete_game(ctx, game)

        else:

            await ctx.send(
                f"**{thisplayer.emoji}<@!{thisplayer.discord_id}> предложил ничью"
                f" to {otherplayer.emoji}<@!{otherplayer.discord_id}>!**"
            )

    @commands.command()
    async def ttimeout(self, ctx: Context):

        try:

            game = self._channel_to_game[str(ctx.channel.id)]

            if ctx.author.id not in game.player_ids:
                await ctx.reply("**Вы не являетесь частью этой игры в крестики-нолики!**")
                return

        except KeyError:

            await ctx.reply("**На этом канале нет игры в крестики-нолики!**")
            return

        if time() - game.timer > game.TIMEOUT:

            game.current_round_player = game.next_player()

            winner = game.current_round_player
            loser = game.next_player()

            await ctx.send(
                f"**{winner.emoji}<@!{winner.discord_id}> побежденный "
                f"{loser.emoji}<@!{loser.discord_id}> из-за бездействия последнего**"
                )

            self.delete_game(ctx, game)

        else:

            await ctx.reply(f"**<@!{game.next_player().discord_id}> имеет еще ~{game.TIMEOUT - (time() - game.timer)}"
                            f" секунды до начала игры!**")

    @classmethod
    async def display(cls, ctx: Context, game: tic.TicTacToeGame):
        txt = game.board.display()

        await ctx.send(f"**ходит игрок <@!{game.current_round_player.discord_id}>'s "
                       f"({game.current_round_player.emoji})**\n")

        # these 2 messages are split, because discord will make emojis smaller when they are combined with normal text

        await ctx.send(txt)

    @classmethod
    def delete_game(cls, ctx: Context, game: tic.TicTacToeGame):

        Game.occupied_channels.remove(ctx.channel.id)
        del cls._channel_to_game[str(ctx.channel.id)]

        for player_id in game.player_ids:

            Player.occupied_players.remove(player_id)

        del game

    @tchallenge.error
    async def tchallenge_error(self, ctx: Context, error: Exception):

        prefix = get_prefix(self.client, ctx)

        if isinstance(error, commands.MissingRequiredArgument):

            await ctx.reply("**Вам нужно указать пользователя!\n"
                            f"Example: {prefix}tchallenge @user**")

        elif isinstance(error, commands.UserNotFound):

            await ctx.reply("**Пользователь не существует или не может быть найден!\n"
                            f"Example: {prefix}tchallenge @user**")

    @p.error
    async def p_error(self, ctx: Context, error: Exception):
        prefix = get_prefix(self.client, ctx)

        if isinstance(error, commands.MissingRequiredArgument):

            await ctx.reply("**Вам нужно указать координаты!\n"
                            f"Example: {prefix}p 4**")

def setup(client):
    client.add_cog(TicTacToeGameCog(client))
