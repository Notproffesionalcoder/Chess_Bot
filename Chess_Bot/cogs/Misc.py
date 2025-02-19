import discord
from discord.ext import commands

import time
import typing
import logging
import sys

import Chess_Bot.util.Utility as util
import Chess_Bot.util.Data as data
from Chess_Bot.cogs.Profiles import Profile
from Chess_Bot.cogs import Profiles as profiles
from Chess_Bot import constants

version = '3.0.0'


class CachedUsernames:

    def __init__(self, client):
        self.client = client
        self.cache = {}

    async def get_username(self, id):
        if id in self.cache.keys() and self.cache[id][1] >= time.time():
            return self.cache[id][0]
        name = str(await self.client.fetch_user(id))
        self.cache[id] = (name, time.time() + constants.CACHE_REFRESH_TIME)
        return name


class Misc(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.start_time = time.time()
        self.cache = CachedUsernames(client)

    @commands.Cog.listener()
    async def on_ready(self):
        game = discord.Game("chess")
        await self.client.change_presence(status=discord.Status.dnd, activity=game)

        status_channel = await self.client.fetch_channel(constants.STATUS_CHANNEL_ID)

        if not '-beta' in sys.argv:
            await status_channel.send(f'Chess Bot has just restarted. Version: {version}')
        else:
            logging.info('Using beta version.')

        logging.info(f'Bot is ready. Logged in as {self.client.user}')

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def ping(self, ctx):
        '''
        {
            "name": "ping",
            "description": "Sends the bot's latency.\\nAccording to the discord.py docs:\\nMeasures latency between a `HEARTBEAT` and a `HEARTBEAT_ACK` in seconds.\\nThis could be referred to as the Discord WebSocket protocol latency.",
            "usage": "$ping",
            "examples": [
                "$ping"
            ],
            "cooldown": 3
        }
        '''
        await ctx.send(f'Pong!\nLatency: {round(self.client.latency * 1000, 3)}ms')

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def rating(self, ctx, person: typing.Union[discord.User, discord.Member] = None):
        '''
        {
            "name": "rating",
            "description": "Tells you a person's rating.\\nIf no person is specified, it defaults to your rating.",
            "usage": "$rating [user]",
            "examples": [
                "$rating",
                "$rating @person"
            ],
            "cooldown": 3
        }
        '''

        if person is None:
            person = ctx.author

        result = data.data_manager.get_rating(person.id)

        if result == None:
            person_str = 'You are' if person == ctx.author else f'{person} is'
            await ctx.send(f'{person_str} unrated.')
        else:
            person_str = 'Your' if person == ctx.author else f'{person}\''
            await ctx.send(f'{person_str} rating is {round(result, 2)}')

    @commands.command(aliases=['top'])
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def leaderboard(self, ctx, num='-1'):
        '''
        {
            "name": "leaderboard",
            "description": "Sends a list of [number] highest rated players.\\nIf a number is not specified, it will default to 10.\\nYou can also enter \\"all\\" for all rated players, or \\"bots\\" for all bots.\\nRight now, the leaderboard can hold a maximum of 40 people.",
            "aliases": [
                "top"
            ],
            "usage": "$leaderboard [number]",
            "examples": [
                "$leaderboard",
                "$leaderboard 13",
                "$leaderboard all",
                "$leaderboard bots"
            ],
            "cooldown": 7
        }
        '''

        embed = discord.Embed(title="Leaderboard", color=0xffb521)

        ratings = data.data_manager.get_ratings()
        all_players = []

        if num == 'bots' or num == 'bot':
            for bot in Profile:
                all_players.append((bot.value, ratings[bot.value]))
            all_players.sort(reverse=True, key=lambda a: a[1])
            embed.set_footer(text='Top rated bots')
        else:
            number = constants.DEFAULT_LEADERBOARD_SIZE
            if num == 'all' or num == 'max':
                number = min(constants.MAX_LEADERBOARD_SIZE,
                             len(ratings.keys()))
            elif num == '-1':
                number = min(constants.DEFAULT_LEADERBOARD_SIZE,
                             len(ratings.keys()))
            else:
                try:
                    number = int(num)
                    assert(1 <= number <= constants.MAX_LEADERBOARD_SIZE)
                except ValueError or AssertionError:
                    await ctx.send('Please enter an integer from 1 to 25.')
                    return

            if number > len(ratings.keys()):
                await ctx.send('There aren\'t even that many rated players.')
                return
            if number > constants.MAX_LEADERBOARD_SIZE:
                await ctx.send('The leaderboard can hold a max of 25 people.')
                return

            embed.set_footer(text=f'Top {number} rated players')

            for k in ratings.keys():
                if k in constants.LEADERBOARD_IGNORE:
                    continue
                all_players.append((k, ratings[k]))
            all_players.sort(reverse=True, key=lambda a: a[1])
            all_players = all_players[:number]

        rows = []
        for i, person in enumerate(all_players):
            if person[0] < len(Profile):
                rows.append(
                    (i + 1, profiles.get_name(person[0]), round(person[1], 2)))
            else:
                rows.append((i + 1, await self.cache.get_username(person[0]), round(person[1], 2)))

        length1 = 0
        length2 = 0
        length3 = 0
        for i in rows:
            length1 = max(length1, len(str(i[0])))
            length2 = max(length2, len(str(i[1])))
            length3 = max(length3, len(str(i[2])))
        for ind, i in enumerate(rows):
            rows[ind] = (' ' * (length1 - len(str(i[0]))) + str(i[0]), ' ' *
                         (length2 - len(i[1])) + i[1], ' ' * (length3 - len(str(i[2]))) + str(i[2]))

        embed.description = '```\n' + \
            '\n'.join([f'{i[0]}: {i[1]} ({i[2]})' for i in rows]) + '\n```'
        embed.set_thumbnail(url=constants.AVATAR_URL)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def rank(self, ctx):
        '''
        {
            "name": "rank",
            "description": "Tells you your rank among all rated players.",
            "usage": "$rank",
            "examples": [
                "$rank"
            ],
            "cooldown": 7
        }
        '''

        if data.data_manager.get_rating(ctx.author.id) is None:
            await ctx.send('You are unrated.')
            return

        ratings = data.data_manager.get_ratings()

        all_players = []

        for k in ratings.keys():
            if k in constants.LEADERBOARD_IGNORE:
                continue
            all_players.append((k, ratings[k]))

        all_players.sort(reverse=True, key=lambda a: a[1])

        rank = None
        for i in range(len(all_players)):
            if all_players[i][0] == ctx.author.id:
                rank = i + 1
                break

        await ctx.send(f'Your rating is {round(data.data_manager.get_rating(ctx.author.id), 2)}. You are ranked {rank} out of {len(all_players)} players.')

    @commands.command(aliases=['info'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def botinfo(self, ctx):
        '''
        {
            "name": "botinfo",
            "description": "Sends some info and stats about the bot.\\nUse `$help` for a list of commands.",
            "aliases": [
                "info"
            ],
            "usage": "$botinfo",
            "examples": [
                "$botinfo"
            ],
            "cooldown": 3
        }
        '''

        embed = discord.Embed(title="Bot Info", color=0xff0000)
        embed.add_field(name="Links",
                        value=f"[Github]({constants.GITHUB_LINK}) | [Invite]({constants.INVITE_LINK}) | [Join the discord server]({constants.SUPPORT_SERVER_INVITE}) | [Top.gg]({constants.TOPGG_LINK})",
                        inline=False)
        embed.add_field(name='Version', value=version, inline=True)
        embed.add_field(name="Info",
                        value='Chess Bot is a bot that plays chess. Use `$help` for a list of commands.', inline=False)

        users = 0
        for guild in self.client.guilds:
            users += guild.member_count

        embed.add_field(name="Stats", value="Stats", inline=False)
        embed.add_field(name="Server Count", value=str(
            len(self.client.guilds)), inline=True)
        embed.add_field(name="Member Count", value=str(users), inline=True)
        embed.add_field(
            name="Up time", value=f'{util.pretty_time(time.time() - self.start_time)}', inline=True)
        embed.add_field(name='Games in progress', value=str(
            len(data.data_manager.get_games())), inline=True)
        embed.add_field(name='Games finished', value=str(
            data.data_manager.total_games()), inline=True)
        owner = (await self.client.application_info()).owner
        embed.set_footer(text=f"Made by {owner}", icon_url=owner.avatar_url)

        embed.set_thumbnail(url=constants.AVATAR_URL)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def invite(self, ctx):
        '''
        {
            "name": "invite",
            "description": "Sends an invite link for adding the bot to a server.",
            "usage": "$invite",
            "examples": [
                "$invite"
            ],
            "cooldown": 1
        }
        '''
        await ctx.send(constants.INVITE_LINK)

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def stats(self, ctx, person: typing.Union[discord.Member, discord.User] = None):
        """
        {
            "name": "stats",
            "description": "Sends stats about the person.",
            "usage": "$stats [person]",
            "examples": [
                "$stats",
                "$stats @person"
            ],
            "cooldown": 3
        }
        """

        if person is None:
            person = ctx.author
        lost, won, drew = data.data_manager.get_stats(person.id)
        embed = discord.Embed(title=f'{person}\'s stats', color=0xfc26e0)
        embed.add_field(name='Rating', value=str(
            data.data_manager.get_rating(person.id)), inline=False)
        embed.add_field(name='Games Played', value=str(
            lost+won+drew), inline=False)
        embed.add_field(name='Lost', value=str(lost))
        embed.add_field(name='Won', value=str(won))
        embed.add_field(name='Drawn', value=str(drew))
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def notif(self, ctx):
        '''
        {
            "name": "notif",
            "description": "Sets the channel for your notifications.",
            "usage": "$notif",
            "examples": [
                "$notif"
            ],
            "cooldown": 3
        }
        '''
        data.data_manager.change_settings(ctx.author.id, new_notif=ctx.channel.id)
        await ctx.send(f'Notification channel set to `{ctx.channel.name}`')


def setup(bot):
    bot.add_cog(Misc(bot))
