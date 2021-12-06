
import discord
from discord.utils import get
from discord.ext import commands
from song import songAPI 
from dotenv import load_dotenv
import os
from keep import keep


load_dotenv('.env')
token = os.getenv('BOT_TOKEN')




bot = commands.Bot(command_prefix='!',help_command=None)

songsInstance = songAPI()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")



@bot.command() 
async def play(ctx,* ,search: str):
    await songsInstance.play(ctx, search)


@bot.command() 
async def p(ctx,* ,search: str):
    await songsInstance.play(ctx, search)

@bot.command()
async def stop(ctx):
    await songsInstance.stop(ctx)

@bot.command()
async def pause(ctx):
    await songsInstance.pause(ctx)

@bot.command()
async def resume(ctx):
    await songsInstance.resume(ctx)

@bot.command()
async def dis(ctx):
    await songsInstance.leave(ctx)

@bot.command()
async def queueList(ctx):
    await songsInstance.queueList(ctx)

@bot.command()
async def skip(ctx):
    await songsInstance.skip(ctx)
    
keep()


bot.run(token)