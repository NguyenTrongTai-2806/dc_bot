import discord
from discord.ext import commands
import os
import asyncio
from utils.rag_engine import RAGEngine

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Khởi tạo bộ não AI khi Cog được tải
        self.rag = RAGEngine()
        
        # Tạo thư mục temp để lưu tạm file tải về
        os.makedirs("temp", exist_ok=True)

    @commands.command(name="learn", help="Dạy bot kiến thức mới từ file đính kèm (.pdf, .txt)")
    @commands.has_permissions(administrator=True) # Chỉ Admin mới được nạp tài liệu
    async def learn(self, ctx):
        # Kiểm tra xem người dùng có đính kèm file không
        if not ctx.message.attachments:
            await ctx.send("❌ Bạn phải đính kèm một file (.pdf hoặc .txt) cùng với lệnh này!")
            return

        attachment = ctx.message.attachments[0]
        
        # Kiểm tra định dạng file
        if not (attachment.filename.endswith('.pdf') or attachment.filename.endswith('.txt')):
            await ctx.send("❌ Bot chỉ hỗ trợ đọc file đuôi `.pdf` và `.txt` thôi nhé.")
            return

        msg = await ctx.send("⏳ Đang tải file xuống và tiến hành băm dữ liệu. Vui lòng chờ...")
        
        # Tải file xuống thư mục tạm
        file_path = f"temp/{attachment.filename}"
        await attachment.save(file_path)

        try:
            # Chạy tác vụ xử lý tài liệu nặng ở luồng khác để bot không bị đơ
            chunks_count = await asyncio.to_thread(self.rag.ingest_document, file_path)
            
            embed = discord.Embed(
                title="🧠 Nạp kiến thức thành công!",
                description=f"Đã xử lý và nạp **{chunks_count}** đoạn văn bản từ file `{attachment.filename}` vào bộ nhớ Vector.",
                color=discord.Color.green()
            )
            await msg.edit(content=None, embed=embed)
            
        except Exception as e:
            await msg.edit(content=f"❌ Có lỗi kỹ thuật xảy ra trong quá trình nạp dữ liệu: {e}")
            
        finally:
            # Dọn dẹp rác: Xóa file tạm sau khi nạp xong để nhẹ máy
            if os.path.exists(file_path):
                os.remove(file_path)

    @commands.command(name="ask", aliases=["hỏi"], help="Hỏi trợ lý AI dựa trên tài liệu đã học.")
    async def ask(self, ctx, *, question: str):
        # Hiện hiệu ứng "Bot đang gõ..." cho chuyên nghiệp
        async with ctx.typing():
            try:
                # Ném tác vụ gọi API Gemini sang luồng khác
                answer = await asyncio.to_thread(self.rag.ask, question)
                
                embed = discord.Embed(
                    title="🤖 Trợ lý AI trả lời:",
                    description=answer,
                    color=discord.Color.purple()
                )
                embed.set_footer(text=f"Câu hỏi từ {ctx.author.name}")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ Não bộ AI đang gặp sự cố: {e}")

    @commands.command(name="clear_brain", help="Xóa sạch bộ nhớ kiến thức (Vector DB) của bot.")
    @commands.has_permissions(administrator=True)
    async def clear_brain(self, ctx):
        await asyncio.to_thread(self.rag.clear_memory)
        await ctx.send("🧹 Đã tẩy não thành công! Trí nhớ của bot hiện tại trống rỗng.")

    @commands.command(name="chat", aliases=["c"], help="Trò chuyện tự do, chém gió với AI.")
    async def chat(self, ctx, *, message: str):
        async with ctx.typing():
            try:
                ans = await asyncio.to_thread(self.rag.chat_freely, str(ctx.author.id), message)
                answer   = ans[0]["text"]
                # --- THÊM DÒNG NÀY ĐỂ DEBUG ---
                # print(f" LOG AI: Độ dài câu trả lời là {len(answer)} ký tự.")
                # print(f" NỘI DUNG AI TRẢ VỀ:\n{answer}\n----------------------")
                # Nếu câu trả lời dài hơn 1500 ký tự, chia nhỏ ra để gửi tránh lỗi Discord
                if len(answer) > 1500:
                    chunks = [answer[i:i+1500] for i in range(0, len(answer), 1500)]
                    for chunk in chunks:
                        await ctx.send(chunk)
                else:
                    await ctx.send(answer)
            except Exception as e:
                await ctx.send(f"❌ Đang gặp sự cố: {e}")

    # Bộ lắng nghe sự kiện: Bot tự động rep khi bị tag
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Bỏ qua tin nhắn của chính bot hoặc các bot khác để tránh lặp vô tận
        if message.author.bot:
            return

        # 2. Kiểm tra xem bot có bị tag trong tin nhắn không
        if self.bot.user.mentioned_in(message):
            # Cắt bỏ phần tag <@id> ra khỏi câu hỏi để AI không bị nhiễu
            clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()

            # Nếu user chỉ tag mà không nói gì thêm
            if not clean_content:
                await message.reply("Kêu mình có việc gì thế? 😊")
                return

            # Hiện hiệu ứng đang gõ và gọi AI
            async with message.channel.typing():
                try:
                    ans = await asyncio.to_thread(self.rag.chat_freely, str(message.author.id), clean_content)
                    answer   = ans[0]["text"]
                    # --- GIẢI PHÁP CHIA NHỎ TIN NHẮN CHO PHẦN MENTION ---
                    if len(answer) > 1500:
                        chunks = [answer[i:i+1500] for i in range(0, len(answer), 1500)]
                        # Tin nhắn đầu tiên thì reply tag người dùng
                        await message.reply(chunks[0])
                        # Các tin nhắn sau thì gửi tiếp nối vào kênh
                        for chunk in chunks[1:]:
                            await message.channel.send(chunk)
                    else:
                        await message.reply(answer)
                except Exception as e:
                    await message.reply(f"❌ Tự nhiên mình bị lú: {e}")
    @commands.command(name="summary", aliases=["tomtat"], help="Tóm tắt nội dung chat gần đây. Cú pháp: !summary [số_tin_nhắn]")
    async def summary(self, ctx, limit: int = 50):
        # Giới hạn số lượng để bot không mất cả thanh xuân để đọc tin nhắn
        if limit <= 0 or limit > 200:
            await ctx.send("❌ Mình chỉ có thể lội từ 1 đến tối đa 200 tin nhắn một lúc thôi nhé!")
            return

        # Báo cho người dùng biết bot đang làm việc
        msg = await ctx.send(f"🕵️ Đang lội lại **{limit}** tin nhắn gần nhất để hóng hớt, mọi người đợi mình xíu...")
        
        try:
            messages = []
            # Lệnh cào lịch sử của Discord (cộng thêm 2 để bỏ qua tin nhắn gọi lệnh của user và tin nhắn thông báo của bot)
            async for m in ctx.channel.history(limit=limit + 2):
                if m.id == ctx.message.id or m.id == msg.id:
                    continue
                
                # Chỉ lấy những tin nhắn có chữ, bỏ qua tin nhắn rỗng (ví dụ người ta chỉ gửi mỗi cái ảnh)
                if m.content.strip():
                    messages.append(f"{m.author.name}: {m.content}")

            if not messages:
                await msg.edit(content="❌ Kênh này vắng như chùa Bà Đanh, không có chữ nào để tóm tắt cả!")
                return

            # Cào lịch sử thì tin nhắn mới nhất sẽ ở đầu danh sách, mình phải lật ngược lại để đúng thứ tự thời gian
            messages.reverse()
            chat_log = "\n".join(messages)

            # Đẩy cục log này cho AI đọc
            summary_text = await asyncio.to_thread(self.rag.summarize_text, chat_log)

            # Thiết kế Embed báo cáo cho ngầu
            embed = discord.Embed(
                title="📋 Báo Cáo Hóng Hớt",
                description=summary_text,
                color=discord.Color.teal()
            )
            embed.set_footer(text=f"Đã tóm tắt từ {len(messages)} tin nhắn.")
            
            # Sửa lại tin nhắn thông báo lúc nãy thành bản báo cáo
            await msg.edit(content=None, embed=embed)

        except Exception as e:
            await msg.edit(content=f"❌ Não bộ thư ký đang bị đình công: {e}")
    
    @commands.command(name="reset", help="Xóa lịch sử trò chuyện của bạn với AI để bắt đầu chủ đề mới.")
    async def reset(self, ctx):
        self.rag.reset_user_memory(str(ctx.author.id))
        await ctx.send("🔄 Mình đã quên hết chuyện cũ của hai đứa mình rồi, bạn muốn nói chuyện gì mới nào?")

# Đăng ký module
async def setup(bot):
    await bot.add_cog(AIChat(bot))