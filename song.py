import discord
from discord.embeds import Embed
from discord.utils import get
import youtube_dl
import asyncio
from async_timeout import timeout
from functools import partial
import itertools
import ytapi

youtube_dl.utils.bug_reports_message = lambda: ""


ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  
}

ffmpeg_options = {
    "options": "-vn",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",  
}


ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get("title")
        self.web_url = data.get("webpage_url")

    def __getitem__(self, item: str):
        return self.__getattribute__(item)

    
    #รับข้อมูลจากฟังก์ชัน play แล้วแปลงข้อมูลที่ได้มาให้เป็นข้อมูลของเพลง
    #แล้วส่งข้อมูลเพลงกลับคืน
    @classmethod 
    async def create_source(cls, ctx, search: str, *, loop):
        loop = loop or asyncio.get_event_loop()
        
        if 'list=' in search:
            playlistid = search.split('list=',1)
            playlistid = playlistid[1]
            if 'index' in playlistid:
                playlistid = playlistid.split('&index=',1)
                playlistid = playlistid[0]
                
            to_run = partial(ytapi.yt_playlist,playlistid,ctx.author)
            data = await loop.run_in_executor(None, to_run)
            return data

        if 'http://' in search:
            to_run = partial(ytdl.extract_info, url=search, download=False)
            data = await loop.run_in_executor(None, to_run)

        else:
            to_run = partial(ytdl.extract_info, url=f'ytsearch:{search}', download=False)
            data = await loop.run_in_executor(None, to_run)
            data = data['entries'][0]

        return {
            'webpage_url': data['webpage_url'],
            'requester': ctx.author,
            'title': data['title'],
            'check': 'True'
        }

    #สร้างข้อมูลในการ streaming เพลง
    @classmethod
    async def stream(cls, data, *, loop):
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']


        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data, requester=requester)


class MusicPlayer:

    __slots__ = (
        "bot",
        "_guild",
        "_channel",
        "_cog",
        "queue",
        "next",
        "current",
        "np",
        "volume",
        "a"
    )

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None
        self.volume = 0.5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    #loop เล่นเพลงที่อยู่ในคิว
    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                async with timeout(300):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return await self.destroy()

            if not isinstance(source, YTDLSource):
                try:
                    source = await YTDLSource.stream(source, loop=self.bot.loop)
                except : continue
            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(
                source,
                after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set),
            )
            em = discord.Embed(
                title="ตอนนี้เรากำลังเล่นเพลง",
                description=f"**`{source.title}`**\n"
                f"คนที่ขอให้เราเล่นเพลงนี้คือ`{source.requester}`",
                color=0xF90716,
            )
            self.np = await self._channel.send(embed=em)
            await self.next.wait()

            source.cleanup()
            self.current = None

            try:
                await self.np.delete()
            except discord.HTTPException:
                pass

    async def destroy(self):
        await self._guild.voice_client.disconnect()
        em = discord.Embed(title="ไม่มีใครเปิดเพลงเลย ", description="งั้นคามุยละ", color=0xF90716)
        await self._channel.send(embed=em)
        del self._guild


class songAPI:
    def __init__(self):
        self.players = {}

    # รับ ข้อมูลจากผู้ใช้แล้วส่งข้อมูลไปให้ฟังก์ชัน create source แล้วนำข้อมูลที่ได้จากฟังก์ชัน create source
    # ไปใส่ไว้ในคิว
    async def play(self, ctx, search: str):
        self.bot = ctx.bot
        self._guild = ctx.guild
        channel = ctx.author.voice.channel
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        _player = self.get_player(ctx)

        if voice_client == None:
            await channel.connect()
            voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        source = await YTDLSource.create_source(
            ctx, search, loop=self.bot.loop)

        addlist = []
        i = 0
        try:
            if source['check'] == 'True':
                print(source)
                await _player.queue.put(source)
                addlist.append(source.get("title"))
        except: pass

        try:
            for item in source:
                await _player.queue.put(item)
                if i <= 10:
                    addlist.append(item["title"])
                i += 1
        except: pass

        if i >= 10:
            left = f"\nและอีก `{i-10}` เพลง"
        else:
            left = f"\n"

        print(addlist)

        listsong = "\n".join(addlist)
        listsong = f"`{listsong}`" + left + "เข้าในคิวเพลงแล้วน้า"

        em = discord.Embed(title="เพิ่มเพลง", description=listsong, color=0xF90716)
        await ctx.channel.send(embed=em)

    #รับข้อมูลของแต่ละเซิฟเวอร์
    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    #พักเพลงที่กำลังเล่นอยู่
    async def pause(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client == None:
            em = discord.Embed(
                title="เอ่อ ..เราทำไม่ได้ เพราะว่าเราไม่ได้อยู่ในห้องเสียงงงง",
                color=0xF90716,
            )
            return await ctx.send(embed=em)

        if voice_client.channel != ctx.author.voice.channel:
            em = discord.Embed(
                title="เอ่อ ..คนสั่งไม่ได้อยู่ในห้องเสียงเดียวกันกับเรา", color=0xF90716
            )
            return await ctx.send(embed=em)

        if voice_client.is_paused():
            em = discord.Embed(
                title="เอ่อ.. เราพักเพลงไม่ได้อ่ะ เพราะเพลงมันพักอยู่แล้ว",
                color=0xF90716,
            )
            return await ctx.send(embed=em)

        voice_client.pause()
        em = discord.Embed(title="เราพักเพลงแล้วนะ", color=0xF90716)
        await ctx.send(embed=em)

    #เล่นเพลงที่พักอยู่
    async def resume(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client == None:
            em = discord.Embed(
                title="เอ่อ ..เราทำไม่ได้ เพราะว่าเราไม่ได้อยู่ในห้องเสียงงงง",
                color=0xF90716,
            )
            return await ctx.send(embed=em)

        if voice_client.channel != ctx.author.voice.channel:
            em = discord.Embed(
                title="เอ่อ ..คนสั่งไม่ได้อยู่ในห้องเสียงเดียวกันกับเรา", color=0xF90716
            )
            return await ctx.send(embed=em)

        if voice_client.is_playing():
            em = discord.Embed(
                title="จะให้เราเล่นต่อได้ไงอ่ะ ก็ในเมื่อไม่ได้กดหยุดเพลงไว้",
                color=0xF90716,
            )
            return await ctx.send(embed=em)

        voice_client.resume()
        em = discord.Embed(title="กลับมาเล่นต่อแล้ว", color=0xF90716)
        await ctx.send(embed=em)

    #เตะบอทออกจากห้องเลียง
    async def leave(self, ctx):
        del self.players[ctx.guild.id]
        await ctx.voice_client.disconnect()
        em = discord.Embed(title="ออกจากห้องแล้วนะ", color=0xF90716)
        await ctx.send(embed=em)

    #แสดงคิวเพลงที่มีอยู่
    async def queueList(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client == None or not voice_client.is_connected():
            em = discord.Embed(
                title="เอ่อ ..เราทำไม่ได้ เพราะว่าเราไม่ได้อยู่ในห้องเสียงงงง",
                color=0xF90716,
            )
            return await ctx.send(embed=em)

        player = self.get_player(ctx)
        if player.queue.empty():
            em = discord.Embed(title="ไม่มีคิวเพลงให้ดูอ่ะ", color=0xF90716)
            return await ctx.send(embed=em)

        new = []
        upcoming = list(itertools.islice(player.queue._queue, 0, player.queue.qsize()))
        print(len(upcoming))
        print(upcoming)
        for i in range(len(upcoming)):
            
            item = upcoming[i]
            try:
                new.append(item["title"])
                if len(new) >= 10:
                    break
            except: 
                if len(upcoming) == 1 :
                    em = discord.Embed(title="ไม่มีคิวเพลงให้ดูอ่ะ", color=0xF90716)
                    return await ctx.send(embed=em)
                pass
        


        if len(new) >= 10:
            left = f"\n\nและอีก `{len(upcoming)-10}` เพลง"
        else:
            left = "\n\nมีแค่นี้แหละ"
        listsong = "\n".join(new)
        listsong = "เพลงต่อไปจะเป็นเพลง\n" + f"`{listsong}`" + left

        em = discord.Embed(
            title=f"คิวเพลงที่เรามีอยู่ เรียงตามนี้เลย",
            description=listsong,
            color=0xF90716,
        )

        await ctx.send(embed=em)

    #ข้ามเพลงที่กำลังเล่นอยู่
    async def skip(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client == None or not voice_client.is_connected():
            em = discord.Embed(
                title="เอ่อ ..เราทำไม่ได้ เพราะว่าเราไม่ได้อยู่ในห้องเสียงงงง",
                color=0xF90716,
            )
            return await ctx.send(embed=em)

        if voice_client.is_paused():
            pass
        elif not voice_client.is_playing():
            return

        voice_client.stop()
        em = discord.Embed(
            title=f"เราข้ามเพลงแล้วนะ",
            description=f"`{ctx.author}` เป็นคนสั่งเรานะ",
            color=0xF90716,
        )
        return await ctx.send(embed=em)

    #ลบคิวเพลงที่มี
    async def clear(self, ctx):
        player = self.get_player(ctx)

        if player.queue.empty():
            em = discord.Embed(title=f"คือแบบ ..ไม่มีเพลงในคิวอ่ะ", color=0xF90716)
            return await ctx.send(embed=em)

        while not player.queue.empty():
            player.queue.get_nowait()

        em = discord.Embed(title=f"เราลบคิวเพลงให้หมดแล้วนะ", color=0xF90716)
        await ctx.send(embed=em)
