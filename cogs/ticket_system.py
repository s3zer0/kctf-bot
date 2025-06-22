import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
from utils.permissions import PermissionManager
from utils.transcript import TranscriptGenerator

class TicketSystem(commands.Cog):
    """티켓 시스템 메인 Cog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.ticket_cooldown = {}
    
    @app_commands.command(name="setup", description="티켓 시스템을 설정합니다")
    @app_commands.default_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        """티켓 시스템 설정 명령어"""
        # 필수 설정 확인
        category = interaction.guild.get_channel(self.bot.ticket_category_id)
        support_role = interaction.guild.get_role(self.bot.support_role_id)
        log_channel = interaction.guild.get_channel(self.bot.log_channel_id)
        
        missing = []
        if not category:
            missing.append("티켓 카테고리")
        if not support_role:
            missing.append("지원팀 역할")
        if not log_channel:
            missing.append("로그 채널")
        
        if missing:
            error_embed = discord.Embed(
                title="❌ 설정 오류",
                description=f"다음 항목들이 설정되지 않았거나 찾을 수 없습니다:\n" + "\n".join(f"• {item}" for item in missing),
                color=discord.Color.red()
            )
            error_embed.add_field(
                name="해결 방법",
                value="1. Discord에서 필요한 채널과 역할을 생성하세요\n2. 개발자 모드를 켜고 ID를 복사하세요\n3. .env 파일을 업데이트하세요",
                inline=False
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        
        # 임베드 생성
        embed = discord.Embed(
            title="새로운 티켓 시스템",
            description="아래 버튼을 이용하여 문의나 도움이 필요한 티켓을 생성하세요.\n담당자가 빠른 시간 내에 응답해드립니다.",
            color=discord.Color.from_str(self.bot.config['bot_settings']['embed_color'])
        )
        embed.add_field(
            name="나의 티켓 생성 시 주의사항",
            value="• 문의사항을 구체적으로 작성해주세요\n• 스크린샷이나 관련 자료를 첨부해주세요\n• 중복 티켓 생성을 자제해주세요",
            inline=False
        )
        embed.set_footer(text="티켓을 생성하려면 아래 버튼을 클릭하세요")
        
        # 버튼 생성
        view = TicketCreateView(self.bot)
        
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="close", description="현재 티켓을 종료합니다")
    async def close_ticket(self, interaction: discord.Interaction):
        """티켓 종료 명령어"""
        # 티켓 채널인지 확인
        ticket_prefix = self.bot.config['bot_settings']['ticket_prefix']
        if not interaction.channel.name.startswith(ticket_prefix):
            await interaction.response.send_message("이 명령어는 티켓 채널에서만 사용할 수 있습니다.", ephemeral=True)
            return
        
        # 권한 확인
        ticket = await self.bot.db.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("이 티켓 정보를 찾을 수 없습니다.", ephemeral=True)
            return
        
        # 티켓 소유자 또는 담당자인지 확인
        is_owner = ticket['user_id'] == interaction.user.id
        is_support = any(role.id == self.bot.support_role_id for role in interaction.user.roles)
        
        if not (is_owner or is_support or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("이 티켓을 종료할 권한이 없습니다.", ephemeral=True)
            return
        
        # 확인 메시지
        embed = discord.Embed(
            title="티켓 종료 확인",
            description="정말로 이 티켓을 종료하시겠습니까?\n티켓을 종료하면 대화 내용이 저장됩니다.",
            color=discord.Color.red()
        )
        
        view = TicketCloseConfirmView(self.bot, interaction.user)
        await interaction.response.send_message(embed=embed, view=view)

class TicketCreateView(discord.ui.View):
    """티켓 생성 버튼 View"""
    
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="새로운 문의 티켓 생성", style=discord.ButtonStyle.primary, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """티켓 생성 버튼"""
        # 쿨다운 확인 (5분)
        user_id = interaction.user.id
        if user_id in self.bot.get_cog('TicketSystem').ticket_cooldown:
            last_time = self.bot.get_cog('TicketSystem').ticket_cooldown[user_id]
            if datetime.datetime.now() - last_time < datetime.timedelta(minutes=5):
                await interaction.response.send_message(
                    "새 티켓 생성은 5분에 한 번만 가능합니다. 잠시 후 다시 시도해주세요.",
                    ephemeral=True
                )
                return
        
        # 티켓 유형 선택 View 표시
        view = TicketTypeSelectView(self.bot)
        embed = discord.Embed(
            title="티켓 유형 선택",
            description="생성하실 티켓의 유형을 선택해주세요.",
            color=discord.Color.from_str(self.bot.config['bot_settings']['embed_color'])
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class TicketTypeSelectView(discord.ui.View):
    """티켓 유형 선택 View"""
    
    def __init__(self, bot):
        super().__init__(timeout=60)
        self.bot = bot
        
        # 티켓 유형 선택 드롭다운
        select = discord.ui.Select(
            placeholder="티켓 유형을 선택하세요",
            options=[
                discord.SelectOption(
                    label=ticket_type['name'],
                    description=ticket_type['description'],
                    emoji=ticket_type['emoji'],
                    value=ticket_type['category']
                )
                for ticket_type in self.bot.config['ticket_types']
            ]
        )
        select.callback = self.select_callback
        self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        """드롭다운 선택 콜백"""
        selected_type = interaction.data['values'][0]
        
        # 선택한 유형으로 모달 표시
        modal = TicketDetailsModal(self.bot, selected_type)
        await interaction.response.send_modal(modal)

class TicketDetailsModal(discord.ui.Modal):
    """티켓 상세 정보 입력 모달"""
    
    def __init__(self, bot, ticket_type):
        super().__init__(title="티켓 생성")
        self.bot = bot
        self.ticket_type = ticket_type
        
        # 문의 내용 입력
        self.description = discord.ui.TextInput(
            label="문의 내용",
            placeholder="문의하실 내용을 자세히 작성해주세요",
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=10,
            max_length=1000
        )
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        """모달 제출 시"""
        # 티켓 채널 생성
        guild = interaction.guild
        category = guild.get_channel(self.bot.ticket_category_id)
        
        if not category:
            await interaction.response.send_message("티켓 카테고리를 찾을 수 없습니다. 관리자에게 문의하세요.", ephemeral=True)
            return
        
        # 지원팀 역할 확인
        support_role = guild.get_role(self.bot.support_role_id)
        if not support_role:
            await interaction.response.send_message("지원팀 역할을 찾을 수 없습니다. 관리자에게 문의하세요.", ephemeral=True)
            return
        
        # 티켓 번호 생성
        ticket_count = len([ch for ch in category.channels if ch.name.startswith(self.bot.config['bot_settings']['ticket_prefix'])])
        ticket_name = f"{self.bot.config['bot_settings']['ticket_prefix']}{ticket_count + 1:04d}-{interaction.user.name}"
        
        # 채널 생성
        channel = await category.create_text_channel(
            name=ticket_name,
            topic=f"티켓 생성자: {interaction.user.mention} | 유형: {self.ticket_type}"
        )
        
        # 권한 설정
        await PermissionManager.setup_channel_permissions(channel, interaction.user, support_role)
        
        # 데이터베이스에 티켓 저장
        ticket_id = await self.bot.db.create_ticket(
            channel.id,
            interaction.user.id,
            self.ticket_type
        )
        
        # 쿨다운 설정
        self.bot.get_cog('TicketSystem').ticket_cooldown[interaction.user.id] = datetime.datetime.now()
        
        # 환영 메시지
        welcome_embed = discord.Embed(
            title=f"새로운 티켓이 생성되었습니다",
            description=self.bot.config['ticket_messages']['welcome'].format(user=interaction.user.mention),
            color=discord.Color.from_str(self.bot.config['bot_settings']['embed_color'])
        )
        
        # 선택한 티켓 유형 정보 찾기
        ticket_type_info = next((t for t in self.bot.config['ticket_types'] if t['category'] == self.ticket_type), None)
        if ticket_type_info:
            welcome_embed.add_field(name="티켓 유형", value=f"{ticket_type_info['emoji']} {ticket_type_info['name']}", inline=True)
        
        welcome_embed.add_field(name="생성일시", value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), inline=True)
        welcome_embed.add_field(name="문의 내용", value=self.description.value, inline=False)
        welcome_embed.set_footer(text="담당자가 곧 응답해드립니다.")
        
        # 티켓 제어 버튼
        view = TicketControlView(self.bot)
        
        await channel.send(
            f"{interaction.user.mention} {support_role.mention}",
            embed=welcome_embed,
            view=view
        )
        
        # 로그
        await self.bot.db.add_ticket_log(ticket_id, 'created', interaction.user.id)
        
        # 로그 채널에 기록
        log_channel = guild.get_channel(self.bot.log_channel_id)
        if log_channel:
            log_embed = discord.Embed(
                title="새로운 티켓 생성",
                color=discord.Color.green()
            )
            log_embed.add_field(name="생성자", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="티켓 채널", value=channel.mention, inline=True)
            log_embed.add_field(name="유형", value=f"{ticket_type_info['emoji']} {ticket_type_info['name']}" if ticket_type_info else self.ticket_type, inline=True)
            log_embed.timestamp = datetime.datetime.now()
            
            await log_channel.send(embed=log_embed)
        
        await interaction.response.send_message(
            f"티켓이 생성되었습니다! {channel.mention}",
            ephemeral=True
        )

class TicketControlView(discord.ui.View):
    """티켓 제어 버튼 View"""
    
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="📌 티켓 담당하기", style=discord.ButtonStyle.primary, custom_id="claim_ticket_button")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """티켓 담당 버튼"""
        # 지원팀 권한 확인
        if not any(role.id == self.bot.support_role_id for role in interaction.user.roles):
            await interaction.response.send_message("지원팀만 티켓을 담당할 수 있습니다.", ephemeral=True)
            return
        
        # 티켓 정보 가져오기
        ticket = await self.bot.db.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("티켓 정보를 찾을 수 없습니다.", ephemeral=True)
            return
        
        # 채널 주제 업데이트
        current_topic = interaction.channel.topic or ""
        if "담당자:" not in current_topic:
            new_topic = f"{current_topic} | 담당자: {interaction.user.mention}"
            await interaction.channel.edit(topic=new_topic)
            
            # 담당 알림 임베드
            embed = discord.Embed(
                title="✅ 티켓 담당자 배정",
                description=f"{interaction.user.mention}님이 이 티켓을 담당합니다.",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"담당 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            await interaction.response.send_message(embed=embed)
            
            # 로그
            await self.bot.db.add_ticket_log(ticket['id'], 'claimed', interaction.user.id)
        else:
            await interaction.response.send_message("이미 담당자가 배정된 티켓입니다.", ephemeral=True)
    
    @discord.ui.button(label="🔒 티켓 종료", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """티켓 종료 버튼"""
        # 권한 확인
        ticket = await self.bot.db.get_ticket_by_channel(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("이 티켓 정보를 찾을 수 없습니다.", ephemeral=True)
            return
        
        is_owner = ticket['user_id'] == interaction.user.id
        is_support = any(role.id == self.bot.support_role_id for role in interaction.user.roles)
        
        if not (is_owner or is_support or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("이 티켓을 종료할 권한이 없습니다.", ephemeral=True)
            return
        
        # 확인 View 표시
        view = TicketCloseConfirmView(self.bot, interaction.user)
        embed = discord.Embed(
            title="티켓 종료 확인",
            description="정말로 이 티켓을 종료하시겠습니까?",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=view)
    
    @discord.ui.button(label="💾 트랜스크립트 저장", style=discord.ButtonStyle.secondary, custom_id="save_transcript")
    async def save_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        """트랜스크립트 저장 버튼"""
        await interaction.response.defer(ephemeral=True)
        
        # 트랜스크립트 생성
        html_file, text_file, message_count = await TranscriptGenerator.save_transcript(interaction.channel)
        
        await interaction.followup.send(
            f"트랜스크립트가 생성되었습니다. (총 {message_count}개 메시지)",
            files=[html_file, text_file],
            ephemeral=True
        )

class TicketCloseConfirmView(discord.ui.View):
    """티켓 종료 확인 View"""
    
    def __init__(self, bot, user):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
    
    @discord.ui.button(label="확인", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """종료 확인 버튼"""
        if interaction.user != self.user:
            await interaction.response.send_message("이 버튼을 사용할 권한이 없습니다.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # 트랜스크립트 생성
        html_file, text_file, message_count = await TranscriptGenerator.save_transcript(interaction.channel)
        
        # 티켓 정보 업데이트
        ticket = await self.bot.db.get_ticket_by_channel(interaction.channel.id)
        if ticket:
            # 데이터베이스 업데이트
            await self.bot.db.close_ticket(interaction.channel.id, interaction.user.id)
            await self.bot.db.add_ticket_log(ticket['id'], 'closed', interaction.user.id)
            
            # 트랜스크립트 저장
            with open(text_file.fp.name, 'rb') as f:
                content = f.read().decode('utf-8')
                await self.bot.db.save_transcript(ticket['id'], content)
            
            # 티켓 생성자에게 DM으로 트랜스크립트 전송
            if self.bot.config['permissions']['transcript_dm']:
                try:
                    user = self.bot.get_user(ticket['user_id'])
                    if user:
                        dm_embed = discord.Embed(
                            title="티켓이 종료되었습니다",
                            description=f"티켓 채널: {interaction.channel.name}\n대화 내용이 첨부되었습니다.",
                            color=discord.Color.blue()
                        )
                        await user.send(embed=dm_embed, files=[
                            discord.File(html_file.fp, filename=f"{interaction.channel.name}_transcript.html"),
                            discord.File(text_file.fp, filename=f"{interaction.channel.name}_transcript.txt")
                        ])
                except:
                    pass
        
        # 로그 채널에 기록
        log_channel = interaction.guild.get_channel(self.bot.log_channel_id)
        if log_channel:
            log_embed = discord.Embed(
                title="티켓 종료",
                color=discord.Color.red()
            )
            log_embed.add_field(name="티켓 채널", value=interaction.channel.name, inline=True)
            log_embed.add_field(name="종료자", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="메시지 수", value=f"{message_count}", inline=True)
            log_embed.timestamp = datetime.datetime.now()
            
            await log_channel.send(embed=log_embed, files=[
                discord.File(html_file.fp, filename=f"{interaction.channel.name}_transcript.html")
            ])
        
        # 종료 메시지
        close_embed = discord.Embed(
            title="티켓이 종료되었습니다",
            description=self.bot.config['ticket_messages']['closed'],
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=close_embed)
        
        # 채널 삭제
        if self.bot.config['permissions']['auto_delete_after_close']:
            await asyncio.sleep(self.bot.config['permissions']['delete_delay_seconds'])
        
        await interaction.channel.delete(reason=f"티켓 종료 - {interaction.user}")
    
    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """종료 취소 버튼"""
        if interaction.user != self.user:
            await interaction.response.send_message("이 버튼을 사용할 권한이 없습니다.", ephemeral=True)
            return
        
        await interaction.response.edit_message(content="티켓 종료가 취소되었습니다.", embed=None, view=None)

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))