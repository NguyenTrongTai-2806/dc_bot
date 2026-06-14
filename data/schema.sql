-- Bảng lưu cấu hình riêng của từng Server Discord
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id INTEGER PRIMARY KEY,      -- ID của Server Discord (Snowflake ID)
    prefix TEXT DEFAULT '!',           -- Prefix tùy chỉnh cho server (mặc định là !)
    mute_role_id INTEGER DEFAULT NULL,  -- ID của role dùng để mute thành viên
    log_channel_id INTEGER DEFAULT NULL -- ID của kênh dùng để ghi log hoạt động
);

-- Bảng lưu lịch sử vi phạm của người dùng (phục vụ lệnh warn/kick/ban)
CREATE TABLE IF NOT EXISTS user_warnings (
    warning_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    moderator_id INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guild_config(guild_id) ON DELETE CASCADE
);

-- Bảng lưu trữ tiền tệ của user
CREATE TABLE IF NOT EXISTS users_money (
    user_id INTEGER PRIMARY KEY,
    wallet INTEGER DEFAULT 0,
    last_daily INTEGER DEFAULT 0
);