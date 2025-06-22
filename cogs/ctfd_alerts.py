import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
from utils.ctfd_api import CTFdAPI
from utils.ctfd_monitor import FirstBloodMonitor
import logging

logger = logging.getLogger(__name__)

class CTFdAlerts(commands.Cog):
    """CTFd First Blood 알림 시스템"""
    
    def __init__(self, bot):
        self.bot = bot
        self.ctfd_api = None
        self.monitor = None
        self.alert_channel_id = None
        self.monitoring_active = False
        
        # CTFd 설정 확인
        self.ctfd_url = os.getenv('CTFD_URL')
        self.ctfd_token = os.getenv('CTFD_API_TOKEN')
        self.poll_interval = int(os.getenv('CTFD_POLL_INTERVAL', '30'))
        
        # 토큰 검증
        if self.ctfd_token and self.ctfd_token.startswith('http'):
            logger.error("CTFd API 토큰이 URL 형태입니다. 실제 토큰을 입력해주세요!")
            self.ctfd_url = None
            self.ctfd_token = None
        elif self.ctfd_url and self.ctfd_token and self.ctfd_token != 'YOUR_ACTUAL_CTFD_TOKEN_HERE':
            try:
                self.ctfd_api = CTFdAPI(self.ctfd_url, self.ctfd_token)
                self.monitor = FirstBloodMonitor(self.ctfd_api)
                logger.info("CTFd 모니터링 시스템 초기화 완료")
            except Exception as e:
                logger.error(f"CTFd API 초기화 실패: {e}")
                self.ctfd_api = None
                self.monitor = None
    
    async def cog_load(self):
        """Cog 로드 시 실행"""
        # 저장된 알림 채널 ID가 있으면 로드
        alert_channel_id = os.getenv('CTFD_ALERT_CHANNEL_ID')
        if alert_channel_id and self.monitor:
            self.alert_channel_id = int(alert_channel_id)
            channel = self.bot.get_channel(self.alert_channel_id)
            if channel:
                self.monitor.set_alert_channel(channel)
                # API 연결 테스트
                if self.ctfd_api and self.ctfd_api.test_connection():
                    # 자동으로 모니터링 시작
                    if not self.check_first_bloods.is_running():
                        self.check_first_bloods.start()
                        self.monitoring_active = True
                        logger.info("CTFd 모니터링 자동 시작")
    
    async def cog_unload(self):
        """Cog 언로드 시 실행"""
        if self.check_first_bloods.is_running():
            self.check_first_bloods.cancel()
    
    @tasks.loop(seconds=30)
    async def check_first_bloods(self):
        """주기적으로 First Blood 확인"""
        if self.monitor and self.monitoring_active:
            await self.monitor.check_for_first_bloods()
    
    @check_first_bloods.before_loop
    async def before_check_first_bloods(self):
        """태스크 시작 전 봇이 준비될 때까지 대기"""
        await self.bot.wait_until_ready()
    
    @app_commands.command(name="ctfd-setup", description="CTFd First Blood 알림을 설정하고 모니터링을 시작합니다")
    @app_commands.default_permissions(administrator=True)
    async def ctfd_setup(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """CTFd 알림 채널 설정 및 모니터링 자동 시작"""
        if not self.ctfd_api:
            embed = discord.Embed(
                title="❌ CTFd 설정 오류",
                description="CTFd API가 설정되지 않았거나 올바르지 않습니다.",
                color=discord.Color.red()
            )
            
            if self.ctfd_token and self.ctfd_token.startswith('http'):
                embed.add_field(
                    name="문제",
                    value="API 토큰이 URL 형태입니다.",
                    inline=False
                )
            elif self.ctfd_token == 'YOUR_ACTUAL_CTFD_TOKEN_HERE':
                embed.add_field(
                    name="문제",
                    value="API 토큰이 설정되지 않았습니다.",
                    inline=False
                )
            
            embed.add_field(
                name="해결 방법",
                value=(
                    "1. CTFd 관리자로 로그인\n"
                    "2. Admin Panel → Settings → Access Tokens\n"
                    "3. 'Generate' 클릭하여 토큰 생성\n"
                    "4. .env 파일의 CTFD_API_TOKEN에 입력\n"
                    "5. 봇 재시작"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 채널이 지정되지 않으면 현재 채널 사용
        target_channel = channel or interaction.channel
        
        # API 연결 테스트
        if not self.ctfd_api.test_connection():
            embed = discord.Embed(
                title="❌ CTFd 연결 실패",
                description="CTFd API에 연결할 수 없습니다.",
                color=discord.Color.red()
            )
            embed.add_field(name="CTFd URL", value=self.ctfd_url, inline=False)
            embed.add_field(
                name="가능한 원인",
                value=(
                    "• API 토큰이 올바르지 않음\n"
                    "• API 토큰이 만료됨\n"
                    "• CTFd 서버가 다운됨\n"
                    "• 네트워크 문제"
                ),
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 알림 채널 설정
        self.alert_channel_id = target_channel.id
        self.monitor.set_alert_channel(target_channel)
        
        # 모니터링 자동 시작
        if not self.check_first_bloods.is_running():
            self.monitoring_active = True
            self.check_first_bloods.start()
            monitoring_status = "🟢 모니터링 시작됨"
        else:
            monitoring_status = "🟢 이미 실행 중"
        
        embed = discord.Embed(
            title="⚙️ CTFd First Blood 알림 설정 완료",
            description=f"First Blood 알림이 {target_channel.mention} 채널로 전송됩니다.",
            color=discord.Color.green()
        )
        embed.add_field(name="CTFd URL", value=self.ctfd_url, inline=False)
        embed.add_field(name="확인 간격", value=f"{self.poll_interval}초", inline=True)
        embed.add_field(name="모니터링 상태", value=monitoring_status, inline=True)
        
        # 현재 문제 정보 추가
        try:
            challenges = self.ctfd_api.get_challenges()
            embed.add_field(
                name="문제 현황",
                value=f"총 {len(challenges)}개의 문제 모니터링 중",
                inline=False
            )
        except:
            pass
        
        await interaction.response.send_message(embed=embed)
        
        # 환경 변수 업데이트 안내
        logger.info(f"CTFd 알림 채널 설정 및 모니터링 시작: {target_channel.name} (ID: {target_channel.id})")

async def setup(bot):
    await bot.add_cog(CTFdAlerts(bot))