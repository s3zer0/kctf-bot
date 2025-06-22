import discord
import aiofiles
import datetime
import io
from PIL import Image, ImageDraw, ImageFont
import textwrap

class TranscriptGenerator:
    """트랜스크립트 생성 클래스"""
    
    @staticmethod
    async def generate_html_transcript(channel: discord.TextChannel, messages: list) -> str:
        """HTML 형식 트랜스크립트 생성"""
        html_template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>트랜스크립트 - {channel_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #36393f;
            color: #dcddde;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: #2f3136;
            border-radius: 8px;
            padding: 20px;
        }}
        .header {{
            border-bottom: 1px solid #202225;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            color: #ffffff;
            font-size: 24px;
        }}
        .header p {{
            margin: 5px 0;
            color: #b9bbbe;
            font-size: 14px;
        }}
        .message {{
            display: flex;
            margin-bottom: 20px;
            padding: 10px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }}
        .message:hover {{
            background-color: #32353b;
        }}
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin-right: 15px;
            background-color: #5865f2;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: white;
        }}
        .message-content {{
            flex: 1;
        }}
        .author {{
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 5px;
        }}
        .timestamp {{
            font-size: 12px;
            color: #72767d;
            margin-left: 10px;
        }}
        .content {{
            color: #dcddde;
            line-height: 1.5;
        }}
        .embed {{
            background-color: #2f3136;
            border-left: 4px solid #5865f2;
            padding: 10px;
            margin-top: 10px;
            border-radius: 4px;
        }}
        .attachment {{
            margin-top: 10px;
            padding: 10px;
            background-color: #202225;
            border-radius: 4px;
            font-size: 14px;
        }}
        .system-message {{
            background-color: #202225;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 10px;
            font-style: italic;
            color: #72767d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>트랜스크립트: {channel_name}</h1>
            <p>생성일: {created_date}</p>
            <p>메시지 수: {message_count}</p>
        </div>
        <div class="messages">
            {messages_html}
        </div>
    </div>
</body>
</html>
        """
        
        messages_html = ""
        for message in reversed(messages):
            # 시스템 메시지 처리
            if message.type != discord.MessageType.default:
                messages_html += f'''
                    <div class="system-message">
                        {message.system_content}
                    </div>
                '''
                continue
            
            # 아바타 첫 글자
            avatar_letter = message.author.display_name[0].upper()
            
            # 메시지 내용 처리
            content = discord.utils.escape_markdown(message.content)
            content = content.replace('\n', '<br>')
            
            # 타임스탬프 포맷
            timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            
            # 첨부파일 처리
            attachments_html = ""
            if message.attachments:
                for attachment in message.attachments:
                    attachments_html += f'''
                        <div class="attachment">
                            첨부 파일: {attachment.filename} ({attachment.size // 1024}KB)
                        </div>
                    '''
            
            # 임베드 처리
            embeds_html = ""
            if message.embeds:
                for embed in message.embeds:
                    embed_content = ""
                    if embed.title:
                        embed_content += f"<strong>{embed.title}</strong><br>"
                    if embed.description:
                        embed_content += f"{embed.description}<br>"
                    
                    if embed_content:
                        embeds_html += f'''
                            <div class="embed">
                                {embed_content}
                            </div>
                        '''
            
            messages_html += f'''
                <div class="message">
                    <div class="avatar">{avatar_letter}</div>
                    <div class="message-content">
                        <div class="author">
                            {message.author.display_name}
                            <span class="timestamp">{timestamp}</span>
                        </div>
                        <div class="content">
                            {content}
                            {attachments_html}
                            {embeds_html}
                        </div>
                    </div>
                </div>
            '''
        
        return html_template.format(
            channel_name=channel.name,
            created_date=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            message_count=len(messages),
            messages_html=messages_html
        )
    
    @staticmethod
    async def generate_text_transcript(channel: discord.TextChannel, messages: list) -> str:
        """텍스트 형식 트랜스크립트 생성"""
        transcript = f"=== 트랜스크립트: {channel.name} ===\n"
        transcript += f"생성일: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        transcript += f"메시지 수: {len(messages)}\n"
        transcript += "=" * 50 + "\n\n"
        
        for message in reversed(messages):
            timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            
            # 시스템 메시지
            if message.type != discord.MessageType.default:
                transcript += f"[시스템] {timestamp}: {message.system_content}\n\n"
                continue
            
            # 일반 메시지
            transcript += f"[{timestamp}] {message.author.display_name}#{message.author.discriminator}:\n"
            transcript += f"{message.content}\n"
            
            # 첨부파일
            if message.attachments:
                transcript += "첨부파일:\n"
                for attachment in message.attachments:
                    transcript += f"  - {attachment.filename} ({attachment.size // 1024}KB)\n"
            
            # 임베드
            if message.embeds:
                transcript += "임베드:\n"
                for embed in message.embeds:
                    if embed.title:
                        transcript += f"  제목: {embed.title}\n"
                    if embed.description:
                        transcript += f"  설명: {embed.description}\n"
            
            transcript += "\n"
        
        return transcript
    
    @staticmethod
    async def save_transcript(channel: discord.TextChannel, limit: int = None) -> tuple:
        """채널 메시지를 트랜스크립트로 저장"""
        messages = []
        async for message in channel.history(limit=limit, oldest_first=True):
            messages.append(message)
        
        # HTML 트랜스크립트 생성
        html_content = await TranscriptGenerator.generate_html_transcript(channel, messages)
        html_file = io.BytesIO(html_content.encode('utf-8'))
        html_file.seek(0)
        
        # 텍스트 트랜스크립트 생성
        text_content = await TranscriptGenerator.generate_text_transcript(channel, messages)
        text_file = io.BytesIO(text_content.encode('utf-8'))
        text_file.seek(0)
        
        return (
            discord.File(html_file, filename=f"{channel.name}_transcript.html"),
            discord.File(text_file, filename=f"{channel.name}_transcript.txt"),
            len(messages)
        )