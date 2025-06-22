import discord
from discord.ext import commands
from discord import app_commands
import datetime

class HelpCommands(commands.Cog):
    """도움말 및 진단 명령어"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="help", description="봇 사용법을 확인합니다")
    async def help_command(self, interaction: discord.Interaction):
        """도움말 명령어"""
        embed = discord.Embed(
            title="📖 Discord 봇 도움말",
            description="티켓 시스템과 CTFd 알림 봇입니다.",
            color=discord.Color.blue()
        )
        
        # 티켓 명령어
        embed.add_field(
            name="🎫 티켓 명령어",
            value=(
                "`/setup` - 티켓 생성 패널 설치 (관리자)\n"
                "`/claim` - 티켓 담당하기 (지원팀)\n"
                "`/close` - 티켓 종료\n"
                "`/add @사용자` - 티켓에 사용자 추가\n"
                "`/remove @사용자` - 티켓에서 사용자 제거\n"
                "`/rename 이름` - 티켓 이름 변경\n"
                "`/topic 주제` - 티켓 주제 변경\n"
                "`/pin 메시지ID` - 메시지 고정"
            ),
            inline=False
        )
        
        # 관리자 명령어
        embed.add_field(
            name="⚙️ 관리자 명령어",
            value=(
                "`/checkconfig` - 봇 설정 확인\n"
                "`/forceclose [채널]` - 티켓 강제 종료\n"
                "`/ticketinfo [채널]` - 티켓 정보 확인\n"
                "`/activetickets` - 활성 티켓 목록\n"
                "`/clearold [일수]` - 오래된 티켓 삭제\n"
                "`/ticketstatsall` - 서버 전체 통계"
            ),
            inline=False
        )
        
        # CTFd 명령어
        embed.add_field(
            name="🏆 CTFd 명령어",
            value=(
                "`/ctfd-setup [채널]` - CTFd 알림 설정\n"
                "`/ctfd-start` - First Blood 모니터링 시작\n"
                "`/ctfd-stop` - 모니터링 중지\n"
                "`/ctfd-status` - 상태 확인\n"
                "`/ctfd-test` - API 연결 테스트\n"
                "`/ctfd-reset` - 알림 기록 초기화"
            ),
            inline=False
        )
        
        embed.set_footer(text="문제가 있으시면 관리자에게 문의하세요!")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="botinfo", description="봇 정보와 권한을 확인합니다")
    async def bot_info(self, interaction: discord.Interaction):
        """봇 정보 명령어"""
        bot_member = interaction.guild.get_member(self.bot.user.id)
        
        embed = discord.Embed(
            title="🤖 봇 정보",
            color=discord.Color.green()
        )
        
        # 기본 정보
        embed.add_field(name="봇 이름", value=self.bot.user.name, inline=True)
        embed.add_field(name="봇 ID", value=self.bot.user.id, inline=True)
        embed.add_field(name="서버 수", value=f"{len(self.bot.guilds)}개", inline=True)
        
        # 권한 확인
        permissions = bot_member.guild_permissions
        required_perms = {
            "채널 관리": permissions.manage_channels,
            "역할 관리": permissions.manage_roles,
            "메시지 전송": permissions.send_messages,
            "임베드 링크": permissions.embed_links,
            "파일 첨부": permissions.attach_files,
            "메시지 기록 읽기": permissions.read_message_history,
            "반응 추가": permissions.add_reactions,
            "슬래시 커맨드": permissions.use_application_commands
        }
        
        perm_text = ""
        for perm, has_perm in required_perms.items():
            perm_text += f"{'✅' if has_perm else '❌'} {perm}\n"
        
        embed.add_field(name="봇 권한", value=perm_text, inline=False)
        
        # 로드된 Cogs
        cogs_list = "\n".join([f"• {cog}" for cog in self.bot.cogs.keys()])
        embed.add_field(name="로드된 모듈", value=cogs_list or "없음", inline=False)
        
        embed.timestamp = datetime.datetime.now()
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="ping", description="봇의 응답 속도를 확인합니다")
    async def ping(self, interaction: discord.Interaction):
        """핑 명령어"""
        latency = round(self.bot.latency * 1000)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"응답 속도: {latency}ms",
            color=discord.Color.green() if latency < 100 else discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCommands(bot))