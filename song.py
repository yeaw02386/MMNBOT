import discord
from discord.embeds import Embed, EmptyEmbed
from discord.utils import get
import youtube_dl
import asyncio
from async_timeout import timeout
from functools import partial
import itertools

youtube_dl.utils.bug_reports_message = lambda: ''
players = {}
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'yesplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5" ## song will end if no this line
}



ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')


    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)
    


    @classmethod

    async def create_source(cls, ctx, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()
        to_run = partial(ytdl.extract_info, url=search, download=download)
        em = discord.Embed(title='รอหน่อยนะ',description='คือเรากำลังจัดการกับเพลงอยู่อาจใช้เวลานานหน่อยนะ'
        ,color=0xF90716) 
        text = await ctx.channel.send(embed=em)
        data = await loop.run_in_executor(None, to_run)
        await text.delete()

        if 'entries' in data:
            return{'data': data}

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source, **ffmpeg_options), data=data, requester=ctx.author)


    
    @classmethod
    async def regather_stream(cls, data, *, loop):
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data, requester=requester)

class MusicPlayer:

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None
        

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        nowplay = None
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                async with timeout(300):  
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                del players[self._guild]
                return await self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                try:
                    
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            nowplay = source.title
            em = discord.Embed(title='ตอนนี้เรากำลังเล่นเพลง',description=f'**`{source.title}`**\n'
                                f'คนที่ขอให้เราเล่นเพลงนี้คือ`{source.requester}`',color=0xF90716)
            self.np = await self._channel.send(embed=em)
            await self.next.wait()


            source.cleanup()
            self.current = None

            try:
                await self.np.delete()
            except discord.HTTPException:
                pass

    async def destroy(self, guild):
        await self._guild.voice_client.disconnect()
        return self.bot.loop.create_task(self._cog.cleanup(guild))


class songAPI:
    def __init__(self):
        self.players = {}

    async def play(self, ctx,search: str):
        self.bot = ctx.bot
        self._guild = ctx.guild
        channel = ctx.author.voice.channel
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        
        if voice_client == None:
            
            await channel.connect()
            voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        _player = self.get_player(ctx)
        source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=False)
        try:
            i = 0
            data = source['data']
            while data['entries'][i] :
                tempdata = data['entries'][i]
                tempsource = {'webpage_url': tempdata['webpage_url'], 'requester': ctx.author, 'title': tempdata['title']}
                await _player.queue.put(tempsource)
                print(tempdata['title'])
                i = i + 1

        except:
            await _player.queue.put(source)

    
    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
        
        return player
        

    async def stop(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client == None:
            em = discord.Embed(title='เอ่อ ..เราทำไม่ได้ เพราะว่าเราไม่ได้อยู่ในห้องเสียงงงง',color=0xF90716)
            return await ctx.send(embed=em)

        if voice_client.channel != ctx.author.voice.channel:
            em = discord.Embed(title='เอ่อ ..คนสั่งไม่ได้อยู่ในห้องเสียงเดียวกันกับเรา',color=0xF90716)
            return await ctx.send(embed=em)

        voice_client.stop()

    async def pause(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client == None:
            em = discord.Embed(title='เอ่อ ..เราทำไม่ได้ เพราะว่าเราไม่ได้อยู่ในห้องเสียงงงง',color=0xF90716)
            return await ctx.send(embed=em)

        if voice_client.channel != ctx.author.voice.channel:
            em = discord.Embed(title='เอ่อ ..คนสั่งไม่ได้อยู่ในห้องเสียงเดียวกันกับเรา',color=0xF90716)
            return await ctx.send(embed=em)

        voice_client.pause()

    async def resume(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client == None:
            em = discord.Embed(title='เอ่อ ..เราทำไม่ได้ เพราะว่าเราไม่ได้อยู่ในห้องเสียงงงง',color=0xF90716)
            return await ctx.send(embed=em)

        if voice_client.channel != ctx.author.voice.channel:
            em = discord.Embed(title='เอ่อ ..คนสั่งไม่ได้อยู่ในห้องเสียงเดียวกันกับเรา',color=0xF90716)
            return await ctx.send(embed=em)

        voice_client.resume()

    async def leave(self, ctx):
        del self.players[ctx.guild.id]
        await ctx.voice_client.disconnect()
        em = discord.Embed(title='ออกจากห้องแล้วนะ',color=0xF90716)
        return await ctx.send(embed=em)

    async def queueList(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client == None or not voice_client.is_connected():
            em = discord.Embed(title='เอ่อ ..เราทำไม่ได้ เพราะว่าเราไม่ได้อยู่ในห้องเสียงงงง',color=0xF90716)
            return await ctx.send(embed=em)
        
        player = self.get_player(ctx)
        if player.queue.empty():
            em = discord.Embed(title='ไม่มีคิวเพลงให้ดูอ่ะ',color=0xF90716)
            return await ctx.send(embed=em)

        new = []
        upcoming = list(itertools.islice(player.queue._queue,0,player.queue.qsize()))
        for i in range(len(upcoming) - 1): 
            item = upcoming[i]
            new.append(item.get('title')) 
            print(item.get('title'))
            if len(new) >= 10:
                break
        
        if len(new) >= 10: left = f'\n\nและอีก `{len(upcoming)-10}` เพลง'
        else : left = '\n\nมีแค่นี้แหละ'
        listsong = f'เพลงต่อไปจะเป็นเพลง\n'+'\n'.join(new) + left 
        
        em = discord.Embed(title=f'คิวเพลงที่เรามีอยู่ เรียงตามนี้เลย', description=listsong,color=0xF90716)

        await ctx.send(embed=em)
        

    async def skip(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client == None or not voice_client.is_connected():
            em = discord.Embed(title='เอ่อ ..เราทำไม่ได้ เพราะว่าเราไม่ได้อยู่ในห้องเสียงงงง',color=0xF90716)
            return await ctx.send(embed=em)

        if voice_client.is_paused():
            pass
        elif not voice_client.is_playing():
            return

        voice_client.stop()
        em = discord.Embed(title=f'{ctx.author} บอกให้เราข้ามเพลง',color=0xF90716)
        return await ctx.send(embed=em)
