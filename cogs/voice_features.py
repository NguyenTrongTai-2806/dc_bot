import discord
from discord.ext import commands
import os
import asyncio
from gtts import gTTS
import yt_dlp

class VoiceFeatures(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Tạo sẵn thư mục để bạn ném mấy file âm thanh tấu hài vào
        os.makedirs("sounds", exist_ok=True) 

    async def join_voice(self, ctx):
        """Hàm phụ trợ giúp bot tự động chui vào kênh Voice của bạn"""
        if not ctx.message.author.voice:
            await ctx.send("Bạn phải vào một kênh thoại trước đã thì mình mới biết đường vào theo chứ!")
            return None
        
        channel = ctx.message.author.voice.channel
        voice_client = ctx.voice_client

        if voice_client and voice_client.is_connected():
            await voice_client.move_to(channel)
        else:
            voice_client = await channel.connect()
        
        return voice_client

    @commands.command(name="leave", aliases=["cút"], help="Đuổi bot khỏi kênh thoại")
    async def leave(self, ctx):
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            await ctx.send("Tạm biệt mọi người, mình lượn đây!")
        else:
            await ctx.send("Mình có ở trong kênh thoại đâu mà đuổi?")

    # ==========================================
    # 1. TÍNH NĂNG CHỊ GOOGLE (TEXT TO SPEECH)
    # ==========================================
    @commands.command(name="say", aliases=["s"], help="Gọi chị Google đọc chữ. Cú pháp: !say [câu nói]")
    async def say(self, ctx, *, text: str):
        voice_client = await self.join_voice(ctx)
        if not voice_client: return

        if voice_client.is_playing():
            voice_client.stop()

        # Biến chữ thành file âm thanh
        tts = gTTS(text=text, lang='vi')
        file_path = f"sounds/tts_{ctx.author.id}.mp3"
        tts.save(file_path)

        # Phát xong thì tự động xóa file để đỡ rác máy
        source = discord.FFmpegPCMAudio(file_path)
        voice_client.play(source, after=lambda e: os.remove(file_path) if os.path.exists(file_path) else None)
        await ctx.send(f"🗣️ **Chị Google đang nói:** {text}")

    # ==========================================
    # 2. TÍNH NĂNG SOUNDBOARD MEME
    # ==========================================
    @commands.command(name="meme", help="Phát âm thanh tấu hài. Cú pháp: !meme [tên file]")
    async def meme(self, ctx, sound_name: str):
        voice_client = await self.join_voice(ctx)
        if not voice_client: return

        file_path = f"sounds/{sound_name}.mp3"
        if not os.path.exists(file_path):
            await ctx.send(f"Không tìm thấy file `{sound_name}.mp3`! Bạn nhớ bỏ file vào thư mục sounds nhé.")
            return

        if voice_client.is_playing():
            voice_client.stop()

        source = discord.FFmpegPCMAudio(file_path)
        voice_client.play(source)

    # ==========================================
    # 3. TÍNH NĂNG PHÁT NHẠC TỪ YOUTUBE
    # ==========================================
    @commands.command(name="play", aliases=["p"], help="Phát nhạc từ YouTube. Cú pháp: !play [tên bài hát]")
    async def play(self, ctx, *, query: str):
        voice_client = await self.join_voice(ctx)
        if not voice_client: return

        if voice_client.is_playing():
            voice_client.stop()

        msg = await ctx.send(f"🔎 Đang lùng sục bài: `{query}`...")

        # Cấu hình lách luật YouTube để stream mượt hơn
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': 'True',
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Nếu bạn gõ tên bài hát thì nó tự search, gõ link thì nó lấy luôn
                if not query.startswith('http'):
                    info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
                else:
                    info = ydl.extract_info(query, download=False)
                
                url = info['url']
                title = info['title']
                
                # Chống giật lag khi mạng yếu
                ffmpeg_options = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                }
                
                source = discord.FFmpegPCMAudio(url, **ffmpeg_options)
                voice_client.play(source)
                await msg.edit(content=f"🎶 Đang quẩy bài: **{title}**")
                
            except Exception as e:
                await msg.edit(content=f"Có biến rồi, bài này YouTube chặn không cho bot phát: {e}")
    
    # ==========================================
    # 4. BỘ LỆNH ĐIỀU KHIỂN NHẠC (STOP / PAUSE / RESUME)
    # ==========================================
    @commands.command(name="stop", help="Tắt hẳn nhạc/âm thanh đang phát. Cú pháp: !stop")
    async def stop(self, ctx):
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await ctx.send("⏹️ Đã tắt nhạc! Trả lại sự im ắng cho phòng thoại.")
        else:
            await ctx.send("Ủa mình có đang phát bài nào đâu?")

    @commands.command(name="pause", help="Tạm dừng bài hát. Cú pháp: !pause")
    async def pause(self, ctx):
        voice_client = ctx.voice_client
        # Phải đang phát nhạc thì mới pause được
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await ctx.send("⏸️ Đã tạm dừng nhạc!")
        else:
            await ctx.send("Có bài nào đang kêu đâu mà đòi tạm dừng?")

    @commands.command(name="resume", help="Tiếp tục phát bài đang bị tạm dừng. Cú pháp: !resume")
    async def resume(self, ctx):
        voice_client = ctx.voice_client
        # Phải đang ở trạng thái pause thì mới resume được
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await ctx.send("▶️ Nhạc lên! Tiếp tục quẩy nào!")
        else:
            await ctx.send("Không có bài nào đang bị tạm dừng cả.")

async def setup(bot):
    await bot.add_cog(VoiceFeatures(bot))