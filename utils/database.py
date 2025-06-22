import aiosqlite
import datetime
import json

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
    
    async def setup(self):
        """데이터베이스 초기화"""
        async with aiosqlite.connect(self.db_path) as db:
            # 티켓 테이블
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    ticket_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    closed_by INTEGER,
                    status TEXT DEFAULT 'open'
                )
            ''')
            
            # 티켓 로그 테이블
            await db.execute('''
                CREATE TABLE IF NOT EXISTS ticket_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
                )
            ''')
            
            # 트랜스크립트 테이블
            await db.execute('''
                CREATE TABLE IF NOT EXISTS transcripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
                )
            ''')
            
            await db.commit()
    
    async def create_ticket(self, channel_id, user_id, ticket_type):
        """새 티켓 생성"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'INSERT INTO tickets (channel_id, user_id, ticket_type) VALUES (?, ?, ?)',
                (channel_id, user_id, ticket_type)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def close_ticket(self, channel_id, closed_by):
        """티켓 종료"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                '''UPDATE tickets 
                   SET status = 'closed', closed_at = CURRENT_TIMESTAMP, closed_by = ? 
                   WHERE channel_id = ?''',
                (closed_by, channel_id)
            )
            await db.commit()
    
    async def get_ticket_by_channel(self, channel_id):
        """채널 ID로 티켓 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM tickets WHERE channel_id = ?',
                (channel_id,)
            )
            return await cursor.fetchone()
    
    async def get_user_tickets(self, user_id):
        """사용자의 모든 티켓 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC',
                (user_id,)
            )
            return await cursor.fetchall()
    
    async def add_ticket_log(self, ticket_id, action, user_id, details=None):
        """티켓 로그 추가"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT INTO ticket_logs (ticket_id, action, user_id, details) VALUES (?, ?, ?, ?)',
                (ticket_id, action, user_id, json.dumps(details) if details else None)
            )
            await db.commit()
    
    async def save_transcript(self, ticket_id, content):
        """트랜스크립트 저장"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT INTO transcripts (ticket_id, content) VALUES (?, ?)',
                (ticket_id, content)
            )
            await db.commit()