import aiosqlite
import os

class DatabaseManager:
    def __init__(self, db_path: str = "data/database.sqlite"):
        self.db_path = db_path

    async def initialize(self):
        """Khởi tạo database và tạo các bảng nếu chưa tồn tại"""
        # Đảm bảo thư mục data/ tồn tại
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Đọc file schema.sql để khởi tạo cấu trúc bảng
            with open("data/schema.sql", "r", encoding="utf-8") as f:
                schema = f.read()
            await db.executescript(schema)
            await db.commit()
        print("[-] Database đã được khởi tạo thành công.")

    async def execute(self, query: str, parameters: tuple = None) -> None:
        """Hàm dùng cho các câu lệnh INSERT, UPDATE, DELETE"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, parameters or ())
            await db.commit()

    async def fetch_one(self, query: str, parameters: tuple = None) -> list:
        """Lấy ra 1 dòng kết quả (SELECT ... LIMIT 1)"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, parameters or ()) as cursor:
                return await cursor.fetchone()

    async def fetch_all(self, query: str, parameters: tuple = None) -> list:
        """Lấy ra toàn bộ dòng kết quả của câu lệnh SELECT"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, parameters or ()) as cursor:
                return await cursor.fetchall()

    # --- CÁC HÀM LOGIC CHO V1 ---

    async def add_guild(self, guild_id: int):
        """Thêm một server mới vào cấu hình khi bot tham gia"""
        query = "INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)"
        await self.execute(query, (guild_id,))

    async def get_prefix(self, guild_id: int) -> str:
        """Lấy prefix của server, nếu không có thì trả về mặc định '!'"""
        query = "SELECT prefix FROM guild_config WHERE guild_id = ?"
        result = await self.fetch_one(query, (guild_id,))
        return result[0] if result else "!"

    async def add_warning(self, guild_id: int, user_id: int, reason: str, moderator_id: int):
        """Ghi nhận một lần cảnh cáo vi phạm của member"""
        query = """
            INSERT INTO user_warnings (guild_id, user_id, reason, moderator_id)
            VALUES (?, ?, ?, ?)
        """
        await self.execute(query, (guild_id, user_id, reason, moderator_id))