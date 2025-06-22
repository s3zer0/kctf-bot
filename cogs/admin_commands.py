import discord
from discord.ext import commands
from discord import app_commands
import datetime
import aiosqlite
from utils.permissions import is_support_staff

class AdminCommands(commands.Cog):
    """관리자 명령어 클래스"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="forceclose", description="티켓을 강제로 종료합니다")
    @app_commands.default_permissions(manage_channels=True)
    async def force_close(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """강제 종료"""
        target_channel = channel or interaction.channel
        
        # 티켓 채널인지 확인
        ticket_prefix = self.bot.config['bot_settings']['ticket_prefix']
        if not target_channel.name.startswith(ticket_prefix):
            await interaction.response.send_message("이것은 티켓 채널이 아닙니다.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # 티켓 정보 조회
        ticket = await self.bot.db.get_ticket_by_channel(target_channel.id)
        if not ticket:
            await interaction.followup.send("이 채널의 티켓 정보를 찾을 수 없습니다.", ephemeral=True)
            return
        
        # 트랜스크립트 생성
        from utils.transcript import TranscriptGenerator
        html_file, text_file, message_count = await TranscriptGenerator.save_transcript(target_channel)
        
        # 데이터베이스 업데이트
        await self.bot.db.close_ticket(target_channel.id, interaction.user.id)
        await self.bot.db.add_ticket_log(
            ticket['id'], 
            'force_closed', 
            interaction.user.id,
            {'reason': 'Admin force close'}
        )
        
        # 트랜스크립트 저장
        with open(text_file.fp.name, 'rb') as f:
            content = f.read().decode('utf-8')
            await self.bot.db.save_transcript(ticket['id'], content)
        
        # 로그 채널에 기록
        log_channel = interaction.guild.get_channel(self.bot.log_channel_id)
        if log_channel:
            log_embed = discord.Embed(
                title="관리자 강제 종료",
                color=discord.Color.orange()
            )
            log_embed.add_field(name="티켓 채널", value=target_channel.name, inline=True)
            log_embed.add_field(name="종료자", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="티켓 생성자", value=f"<@{ticket['user_id']}>", inline=True)
            log_embed.timestamp = datetime.datetime.now()
            
            await log_channel.send(embed=log_embed)
        
        # 채널 삭제
        await target_channel.delete(reason=f"강제 종료 - {interaction.user}")
        
        if interaction.channel != target_channel:
            await interaction.followup.send(f"티켓 {target_channel.name}이 강제로 종료되었습니다.")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))