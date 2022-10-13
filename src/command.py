from discord.utils import get
import discord
import Player
import itertools


class songAPI:
    def __init__(self):
        self.players = {}

    
    #รับข้อมูลของแต่ละเซิฟเวอร์
    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except:
            player = Player.MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    #เช็คความพร้อมของบอท
    def ready(self,voice_client,ctx):
        if voice_client == None:
            em = discord.Embed(
                title="เอ่อ ..เราทำไม่ได้ เพราะว่าเราไม่ได้อยู่ในห้องเสียงงงง",
                color=0xF90716,
            )

            return em

        if voice_client.channel != ctx.author.voice.channel:
            em = discord.Embed(
                title="เอ่อ ..คนสั่งไม่ได้อยู่ในห้องเสียงเดียวกันกับเรา", color=0xF90716
            )
            return em

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

        source,_player.que = await Player.YTDLSource.create_source(
                    ctx, search, loop=self.bot.loop,que=_player.que)

        addlist = []
        i = 0
        try:
            if source['check'] == 'True':
                await _player.queue.put(source)
                temp = f"คิวที่ `{source['queue']}` : `{source['title']}`"
                addlist.append(temp)
        except: 
            for item in source:
                await _player.queue.put(item)
                if i <= 5:
                    temp = f"คิวที่ `{item['queue']}` : `{item['title']}`"
                    addlist.append(temp)
                i += 1

        if i >= 5:
            left = f"\nและอีก `{i-5}` เพลง"
        else:
            left = ""

        listsong = "\n".join(addlist) + left + "เข้าในคิวเพลงแล้วน้า"

        em = discord.Embed(title="เพิ่มเพลง", description=listsong, color=0xF90716)
        await ctx.channel.send(embed=em)


    #พักเพลงที่กำลังเล่นอยู่
    async def pause(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        _ready = self.ready(voice_client,ctx)
        if _ready :
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
        _ready = self.ready(voice_client,ctx)
        if _ready :
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

        _ready = self.ready(voice_client,ctx)
        if _ready :
            return await ctx.send(embed=em)

        player = self.get_player(ctx)
        if player.queue.empty():
            em = discord.Embed(title="ไม่มีคิวเพลงให้ดูอ่ะ", color=0xF90716)
            return await ctx.send(embed=em)

        new = []
        np = player.current
        upcoming = list(itertools.islice(player.queue._queue, 0, player.queue.qsize()))

        for item in upcoming:
            temp = f"คิวที่ี `{item['queue']}` : `{item['title']}`"
            new.append(temp)
            if len(new) >= 10:
                break

        if len(new) >= 10:
            left = f"\n\nและอีก `{len(upcoming)-10}` เพลง"
        else:
            left = "\n\nมีแค่นี้แหละ"
        listsong = "\n".join(new)
        listsong = (f"ตอนนี้เรากำลังเล่นเพลง\nคิวที่ `{np.que}` : `{np.title}`\n"
                    +"เพลงต่อไปจะเป็นเพลง\n\n" + listsong + left)

        em = discord.Embed(
            title=f"คิวเพลงที่เรามีอยู่ เรียงตามนี้เลย",
            description=listsong,
            color=0xF90716,
        )
        await ctx.send(embed=em)


    #ข้ามเพลงที่กำลังเล่นอยู่
    async def skip(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        player = self.get_player(ctx)

        _ready = self.ready(voice_client,ctx)
        if _ready :
            return await ctx.send(embed=em)

        if voice_client.is_paused():
            pass
        elif not voice_client.is_playing():
            return

        voice_client.stop()
        np = player.current
        em = discord.Embed(
            title=f"เราข้ามเพลงคิวที่ `{np.que}`",
            description=f"[{np.title}]({np.webpage_url})\n\n`{ctx.author.name}` เป็นคนสั่งเรานะ",
            color=0xF90716
        )
        em.set_thumbnail(url=np.thumbnails)
        await ctx.send(embed=em)


    #ลบคิวเพลงที่มี
    async def clear(self, ctx):
        player = self.get_player(ctx)

        if player.queue.empty():
            em = discord.Embed(title=f"คือแบบ ..ไม่มีเพลงในคิวอ่ะ", color=0xF90716)
            return await ctx.send(embed=em)

        while not player.queue.empty():
            player.queue.get_nowait()
        player.que = 1
        em = discord.Embed(title=f"เราลบคิวเพลงให้หมดแล้วนะ", color=0xF90716)
        await ctx.send(embed=em)