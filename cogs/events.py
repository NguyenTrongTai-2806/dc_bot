import discord
from discord.ext import commands
import traceback

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Sự kiện 1: Chào mừng người mới
    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Gửi một tin nhắn riêng (DM) cực xịn cho người mới
        try:
            embed = discord.Embed(
                title="🎉 Chào mừng bạn đã tới!",
                description=f"Chào {member.mention}, chúc bạn có khoảng thời gian vui vẻ tại **{member.guild.name}** nhé!",
                color=discord.Color.blue()
            )
            await member.send(embed=embed)
        except discord.Forbidden:
            # Nếu người ta khóa tin nhắn riêng (DM) thì mình cứ kệ thôi, bỏ qua lỗi này
            pass

    # Sự kiện 2: Bắt lỗi toàn hệ thống
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # 1. Bỏ qua lỗi gõ sai tên lệnh (để bot không spam báo lỗi khi người ta gõ bậy bạ)
        if isinstance(error, commands.CommandNotFound):
            return

        # 2. Lỗi user không có quyền nhưng cứ thích xài lệnh admin
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bạn không có đủ quyền để xài lệnh này!")
            return

        # 3. Lỗi user gõ thiếu chữ (VD: gõ !warn nhưng quên tag tên người bị warn)
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠️ Bạn gõ thiếu thông tin rồi. Cú pháp đúng: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`")
            return

        if isinstance(error, commands.CommandOnCooldown):
            # Quy đổi số giây ra giờ, phút, giây cho thân thiện
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            
            await ctx.send(f"⏳ Quá Tham lam! Bạn phải chờ **{int(hours)} giờ {int(minutes)} phút** nữa mới được nhận coins tiếp.")
            return

        # 4. Các lỗi kỹ thuật khác thì in ra Terminal để mình đọc và sửa
        print(f"[!] Bắt được lỗi từ lệnh {ctx.command}:")
        traceback.print_exception(type(error), error, error.__traceback__)

# Khai báo để main.py có thể load được file này
async def setup(bot):
    await bot.add_cog(Events(bot))