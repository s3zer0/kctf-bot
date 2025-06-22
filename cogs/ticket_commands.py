import discord
from discord.ext import commands
from discord import app_commands
import datetime

class TicketCommands(commands.Cog):
    """티켓 관련 명령어 (현재 사용하지 않음)"""
    
    def __init__(self, bot):
        self.bot = bot
    
    # 모든 명령어 제거됨 - 필수 명령어는 다른 Cog에 있음

async def setup(bot):
    await bot.add_cog(TicketCommands(bot))