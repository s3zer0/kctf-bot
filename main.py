import discord
from discord.ext import commands
import os
import json
import asyncio
from dotenv import load_dotenv
import logging
import sys
import datetime

# 환경 변수 로드
load_dotenv()

# 로깅 설정
debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
logging.basicConfig(
    level=logging.DEBUG if debug_mode else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('discord_ticket_bot')

# Discord 로깅 레벨 조정 (너무 많은 로그 방지)
if not debug_mode:
    logging.getLogger('discord').setLevel(logging.WARNING)

# 인텐트 설정
intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # 멤버 정보 접근에 필요 (특권 인텐트)

class TicketBot(commands.Bot):
    def __init__(self):
        # 설정 파일 로드
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                logger.info("config.json 로드 성공")
        except Exception as e:
            logger.error(f"config.json 로드 실패: {e}")
            sys.exit(1)
        
        super().__init__(
            command_prefix=self.config['bot_settings']['prefix'],
            intents=intents,
            help_command=None
        )
        
        # 환경 변수 확인
        try:
            self.guild_id = int(os.getenv('GUILD_ID'))
            self.log_channel_id = int(os.getenv('LOG_CHANNEL_ID'))
            self.ticket_category_id = int(os.getenv('TICKET_CATEGORY_ID'))
            self.support_role_id = int(os.getenv('SUPPORT_ROLE_ID'))
            self.admin_role_id = int(os.getenv('ADMIN_ROLE_ID'))
            logger.info("환경 변수 로드 성공")
        except Exception as e:
            logger.error(f"환경 변수 로드 실패: {e}")
            logger.error("필수 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
            sys.exit(1)
    
    async def setup_hook(self):
        logger.info("setup_hook 시작")
        
        # 데이터베이스 초기화
        try:
            from utils.database import Database
            self.db = Database('tickets.db')
            await self.db.setup()
            logger.info("데이터베이스 초기화 성공")
        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")
        
        # Cogs 로드 - 필요한 것만 명시적으로 로드
        initial_extensions = [
            'cogs.ticket_system',    # setup, close 명령어
            'cogs.admin_commands',   # forceclose 명령어
            'cogs.ctfd_alerts'       # ctfd-setup 명령어
        ]
        
        # help_commands가 있으면 로드 (선택사항)
        if os.path.exists('./cogs/help_commands.py'):
            initial_extensions.append('cogs.help_commands')
        
        logger.info(f"로드할 Cogs: {initial_extensions}")
        
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f'✅ Loaded cog: {extension}')
            except Exception as e:
                logger.error(f'❌ Failed to load cog {extension}: {e}')
                if debug_mode:
                    import traceback
                    logger.error(traceback.format_exc())
    
    async def on_ready(self):
        logger.info(f'{self.user} 봇이 시작되었습니다!')
        logger.info(f'봇 ID: {self.user.id}')
        logger.info(f'서버 수: {len(self.guilds)}')
        
        # 활동 상태 설정
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="티켓 도움말 | /help"
        )
        await self.change_presence(activity=activity)
        
        # Slash 명령어 동기화
        try:
            # 특정 길드에만 동기화 (빠른 업데이트)
            guild = discord.Object(id=self.guild_id)
            
            # 기존 명령어 삭제 후 재등록 (디버그 모드에서만)
            if debug_mode:
                logger.info("디버그 모드: 기존 명령어 삭제 중...")
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info("기존 명령어 삭제 완료")
            
            # 명령어 동기화
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info(f'✅ {len(synced)}개의 slash 명령어가 길드 {self.guild_id}에 동기화되었습니다.')
            
            # 사용 가능한 명령어 출력
            logger.info("=== 사용 가능한 명령어 ===")
            commands_list = []
            for command in self.tree.get_commands(guild=guild):
                commands_list.append(f"/{command.name} - {command.description}")
                logger.info(f"  /{command.name} - {command.description}")
            
            # 로그 채널에도 알림
            log_channel = self.get_channel(self.log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="✅ 봇 시작됨",
                    description=f"총 {len(commands_list)}개의 명령어가 로드되었습니다.",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.now()
                )
                embed.add_field(
                    name="명령어 목록",
                    value="\n".join(commands_list[:10]) + (f"\n... 외 {len(commands_list)-10}개" if len(commands_list) > 10 else ""),
                    inline=False
                )
                await log_channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f'❌ Slash 명령어 동기화 실패: {e}')
            if debug_mode:
                import traceback
                logger.error(traceback.format_exc())

async def main():
    logger.info("봇 시작 중...")
    bot = TicketBot()
    
    try:
        async with bot:
            await bot.start(os.getenv('DISCORD_TOKEN'))
    except discord.LoginFailure:
        logger.error("❌ 봇 토큰이 올바르지 않습니다. .env 파일의 DISCORD_TOKEN을 확인하세요.")
    except Exception as e:
        logger.error(f"❌ 봇 실행 중 오류 발생: {e}")
        if debug_mode:
            import traceback
            logger.error(traceback.format_exc())

if __name__ == '__main__':
    # Python 버전 확인
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 이상이 필요합니다.")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("봇이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"치명적 오류: {e}")
        if debug_mode:
            import traceback
            logger.error(traceback.format_exc())