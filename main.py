import discord
from discord.ext import commands
from song import songAPI 
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('TOKEN')


bot = commands.Bot(command_prefix='-',help_command=None)
songsInstance = songAPI()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.command()
async def help(ctx):
    em = discord.Embed(title='คำสั่งทั้งหมดนะ',
    description='ตัว prefix ของเราคือ ! นะ \nสำหรับคำสั่งที่เรามีนะ คือ'
    ,color=0xF90716)
    em.add_field(name='p  หรือ play',value='บอกให้เราเปิดเพลง',inline=False)
    em.add_field(name='sp หรือ skip',value='ให้เราข้ามเพลงที่กำลังเล่นอยู่',inline=False)
    em.add_field(name='ls หรือ list',value='ให้เราบอกคิวเพลงที่มีอยู่ตอนนี้',inline=False)
    em.add_field(name='pu หรือ pause',value='ให้เราหยุดเล่นเพลงก่อน',inline=False)
    em.add_field(name='re หรือ resume',value='ให้เรากลับมาเล่นเพลงต่อ',inline=False)
    em.add_field(name='cl หรือ clear',value='ให้เราลบคิวเพลงทั้งหมด',inline=False)
    em.add_field(name='le หรือ leave',value='ไล่เราออกจากช่องเสียง',inline=False)
    
    await ctx.channel.send(embed=em)

@bot.command() 
async def play(ctx,* ,search: str):
    await songsInstance.play(ctx, search)

@bot.command() 
async def p(ctx,* ,search: str):
    await songsInstance.play(ctx, search)

@bot.command()
async def pause(ctx):
    await songsInstance.pause(ctx)

@bot.command()
async def pu(ctx):
    await songsInstance.pause(ctx)

@bot.command()
async def resume(ctx):
    await songsInstance.resume(ctx)

@bot.command()
async def re(ctx):
    await songsInstance.resume(ctx)

@bot.command()
async def leave(ctx):
    await songsInstance.leave(ctx)

@bot.command()
async def le(ctx):
    await songsInstance.leave(ctx)

@bot.command()
async def list(ctx):
    await songsInstance.queueList(ctx)

@bot.command()
async def ls(ctx):
    await songsInstance.queueList(ctx)

@bot.command()
async def skip(ctx):
    await songsInstance.skip(ctx)

@bot.command()
async def sp(ctx):
    await songsInstance.skip(ctx)

@bot.command()
async def clear(ctx):
    await songsInstance.clear(ctx)

@bot.command()
async def cl(ctx):
    await songsInstance.clear(ctx)
    


bot.run(token)