import discord
from discord.ext import commands

class PermissionManager:
    """권한 관리 클래스"""
    
    @staticmethod
    async def setup_channel_permissions(channel: discord.TextChannel, user: discord.Member, support_role: discord.Role):
        """티켓 채널 권한 설정"""
        overwrites = {
            # 기본 역할 - 모든 권한 거부
            channel.guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
                send_messages=False,
                read_message_history=False,
                attach_files=False,
                embed_links=False
            ),
            # 티켓 생성자 권한
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                add_reactions=True
            ),
            # 지원팀 권한
            support_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                add_reactions=True,
                manage_messages=True
            ),
            # 봇 권한
            channel.guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                add_reactions=True,
                manage_messages=True,
                manage_channels=True
            )
        }
        
        await channel.edit(overwrites=overwrites)
        return True
    
    @staticmethod
    def has_ticket_access(member: discord.Member, channel: discord.TextChannel, support_role_id: int) -> bool:
        """멤버가 티켓에 접근 권한이 있는지 확인"""
        # 관리자 권한 확인
        if member.guild_permissions.administrator:
            return True
        
        # 지원팀 역할이 있는지 확인
        if any(role.id == support_role_id for role in member.roles):
            return True
        
        # 채널 권한 확인
        permissions = channel.permissions_for(member)
        return permissions.view_channel and permissions.send_messages
    
    @staticmethod
    def is_ticket_owner(member: discord.Member, channel: discord.TextChannel) -> bool:
        """멤버가 티켓 소유자인지 확인"""
        # 채널 권한에서 확인
        overwrites = channel.overwrites_for(member)
        return overwrites.view_channel is True and overwrites.send_messages is True
    
    @staticmethod
    async def add_user_to_ticket(channel: discord.TextChannel, user: discord.Member):
        """티켓에 사용자 추가"""
        await channel.set_permissions(
            user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )
    
    @staticmethod
    async def remove_user_from_ticket(channel: discord.TextChannel, user: discord.Member):
        """티켓에서 사용자 제거"""
        await channel.set_permissions(
            user,
            view_channel=False,
            send_messages=False,
            read_message_history=False
        )

def is_support_staff():
    """지원팀 확인 데코레이터"""
    async def predicate(ctx):
        if ctx.guild is None:
            return False
        
        support_role_id = ctx.bot.support_role_id
        admin_role_id = ctx.bot.admin_role_id
        
        # 관리자 권한 확인
        if ctx.author.guild_permissions.administrator:
            return True
        
        # 지원팀 또는 관리자 역할 확인
        role_ids = [role.id for role in ctx.author.roles]
        return support_role_id in role_ids or admin_role_id in role_ids
    
    return commands.check(predicate)

def is_ticket_channel():
    """티켓 채널 확인 데코레이터"""
    async def predicate(ctx):
        if ctx.guild is None:
            return False
        
        # 채널 이름이 티켓 접두사로 시작하는지 확인
        ticket_prefix = ctx.bot.config['bot_settings']['ticket_prefix']
        return ctx.channel.name.startswith(ticket_prefix)
    
    return commands.check(predicate)