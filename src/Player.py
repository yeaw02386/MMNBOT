import discord
import youtube_dl
import asyncio
import time
from async_timeout import timeout
from functools import partial
import ytapi

youtube_dl.utils.bug_reports_message = lambda: ""
ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(duation)s-%(id)s-%(title)s.%(ext)s",
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
    def __init__(self, source,data,dur):
        super().__init__(source)
        self.requester = data['requester']
        self.title = data['title']
        self.webpage_url = data['webpage_url']
        self.thumbnails = data['thumbnails']
        self.que = data['queue']
        self.duration = dur

    def __getitem__(self, item: str):
        return self.__getattribute__(item)

    
    #รับข้อมูลจากฟังก์ชัน play แล้วแปลงข้อมูลที่ได้มาให้เป็นข้อมูลของเพลง
    #แล้วส่งข้อมูลเพลงกลับคืน
    @classmethod 
    async def create_source(cls, ctx, search: str, *, loop,que):
        loop = loop or asyncio.get_event_loop()
        

        if 'list=' in search:
            playlistid = search.split('list=')[1]
            if 'index' in playlistid:
                playlistid = playlistid.split('&index=',1)[0]
                
            to_run = partial(ytapi.yt_playlist,playlistid,ctx.author.name,que)
            data,que = await loop.run_in_executor(None, to_run)
            return data,que

        if 'https://' in search:
            data = ytdl.extract_info(url=search,download=False)['id']
            to_run = partial(ytapi.yt_video,data,ctx.author.name,que)
            data,que = await loop.run_in_executor(None, to_run)

        else:
            data = ytdl.extract_info(url=f'ytsearch:{search}', download=False)['entries'][0]['id']
            to_run = partial(ytapi.yt_video,data,ctx.author.name,que)
            data,que = await loop.run_in_executor(None, to_run)

        return data,que

    #สร้างข้อมูลในการ streaming เพลง
    @classmethod
    async def stream(cls, source, *, loop):
        loop = loop or asyncio.get_event_loop()
        to_run = partial(ytdl.extract_info, url=source['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)
        dur = time.strftime('%H:%M:%S', time.gmtime(data.get('duration')))

        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options),data=source,dur=dur)


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
        "que"
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
        self.que = 1

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

            source = await YTDLSource.stream(source, loop=self.bot.loop)
            source.volume = self.volume
            self.current = source
            self._guild.voice_client.play(
                source,
                after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set),
            )
            em = discord.Embed(title=f"ตอนนี้เรากำลังเล่นเพลงของคิวที่ `{source.que}`",
            description=f"[{source.title}]({source.webpage_url})\n\n"
            f"ความยาวเพลงนี้ก็คือ `{source.duration}` แล้วก็ `{source.requester}`เป็นคนบอกเราให้เล่นเพลงนี้นะ"
            ,color=0xF90716)
            
            em.set_thumbnail(url=source.thumbnails)
            self.np = await self._channel.send(embed=em)

            await self.next.wait()
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
