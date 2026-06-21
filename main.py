from flask import Flask
from threading import Thread
import os as os_module
import sys

# ============================================================
# FLASK KEEP-ALIVE
# ============================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask).start()

# ============================================================
# MAIN BOT - FULL: AUTO SETUP + GAME + MINI GAMES + NSFW
# ============================================================
import discord
from discord.ext import commands
from discord import app_commands
import json
import base64
import time
import random
import asyncio
import glob
from datetime import datetime, timedelta
import aiohttp
from typing import Optional, Dict, List, Any
from io import BytesIO

# Optional imports
try:
    from bs4 import BeautifulSoup
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    pass

# ============================================================
# CONFIG
# ============================================================
BOT_TOKEN: str = os_module.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("❌ Chưa set BOT_TOKEN trong Secrets!")
    sys.exit(1)

intents: discord.Intents = discord.Intents.all()
bot: commands.Bot = commands.Bot(command_prefix="!", intents=intents)

user_tokens: Dict[int, str] = {}
players: Dict[int, Dict[str, Any]] = {}

# ============================================================
# NSFW DATA (GIỮ TỪ TOOL CŨ)
# ============================================================
NSFW_DIR = "nsfw_images"
if not os_module.path.exists(NSFW_DIR):
    os_module.makedirs(NSFW_DIR)

NSFW_CATEGORIES = {
    "waifu": os_module.path.join(NSFW_DIR, "waifu"),
    "neko": os_module.path.join(NSFW_DIR, "neko"),
    "trap": os_module.path.join(NSFW_DIR, "trap"),
    "blowjob": os_module.path.join(NSFW_DIR, "blowjob"),
    "hentai": os_module.path.join(NSFW_DIR, "hentai"),
    "boobs": os_module.path.join(NSFW_DIR, "boobs"),
    "pussy": os_module.path.join(NSFW_DIR, "pussy"),
    "anal": os_module.path.join(NSFW_DIR, "anal"),
    "gonewild": os_module.path.join(NSFW_DIR, "gonewild"),
}
for cat_dir in NSFW_CATEGORIES.values():
    if not os_module.path.exists(cat_dir):
        os_module.makedirs(cat_dir)

nsfw_web_cache = {}
cache_timestamp = {}

HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "vi-VN,vi;q=0.9"
}

# ============================================================
# MINI GAME DATA
# ============================================================
mini_game_players = {
    "blackjack": {},
    "minesweeper": {},
    "slot_machines": {},
    "archery": {},
}

SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣", "🌟", "💰", "🔔", "🍀"]
SLOT_PAYOUTS = {
    "🍒🍒🍒": 50, "🍋🍋🍋": 75, "🍊🍊🍊": 100,
    "🍇🍇🍇": 150, "💎💎💎": 500, "7️⃣7️⃣7️⃣": 1000,
    "🌟🌟🌟": 200, "💰💰💰": 300, "🔔🔔🔔": 125, "🍀🍀🍀": 250,
}

CARD_SUITS = ["♠", "♥", "♦", "♣"]
CARD_VALUES = {"A": 11, "K": 10, "Q": 10, "J": 10, "10": 10, "9": 9, "8": 8, "7": 7, "6": 6, "5": 5, "4": 4, "3": 3, "2": 2}
CARD_NAMES = list(CARD_VALUES.keys())

# ============================================================
# AUTO SERVER CONFIG (CÓ NSFW ZONE)
# ============================================================
AUTO_SERVER_CONFIG = {
    "roles": [
        {"name": "👑 Admin", "color": 0xff0000, "permissions": ["administrator"], "hoist": True},
        {"name": "🛡️ Mod", "color": 0x00ff00, "permissions": ["kick_members", "ban_members", "manage_messages"], "hoist": True},
        {"name": "💎 VIP", "color": 0xffd700, "permissions": [], "hoist": True},
        {"name": "⚔️ Game Master", "color": 0x9b59b6, "permissions": [], "hoist": True},
        {"name": "🎮 Gamer", "color": 0x3498db, "permissions": [], "hoist": True},
        {"name": "🔞 NSFW Access", "color": 0xe91e63, "permissions": [], "hoist": True},
        {"name": "🤖 Bot", "color": 0x95a5a6, "permissions": [], "hoist": False},
    ],
    "categories": [
        {"name": "📢 THÔNG BÁO", "position": 0},
        {"name": "💬 CHAT CHUNG", "position": 1},
        {"name": "⚔️ GAME ZONE", "position": 2},
        {"name": "🎲 MINI GAMES", "position": 3},
        {"name": "🔞 NSFW ZONE", "position": 4},
        {"name": "🛡️ STAFF ONLY", "position": 5},
    ],
    "channels": [
        # Thông báo
        {"name": "📋-luật-lệ", "category": "📢 THÔNG BÁO", "type": "text", "topic": "📜 Nội quy server"},
        {"name": "📣-thông-báo", "category": "📢 THÔNG BÁO", "type": "text", "topic": "📢 Thông báo"},
        {"name": "👋-chào-mừng", "category": "📢 THÔNG BÁO", "type": "text", "topic": "👋 Welcome"},
        # Chat chung
        {"name": "💬-chat-chính", "category": "💬 CHAT CHUNG", "type": "text", "topic": "💬 Chat thoải mái"},
        {"name": "😂-spam-chill", "category": "💬 CHAT CHUNG", "type": "text", "topic": "😂 Spam chill"},
        {"name": "📸-media", "category": "💬 CHAT CHUNG", "type": "text", "topic": "📸 Media"},
        {"name": "🔊 Voice Chill", "category": "💬 CHAT CHUNG", "type": "voice"},
        # Game zone
        {"name": "⚔️-đấu-trường", "category": "⚔️ GAME ZONE", "type": "text", "topic": "⚔️ PvP đấu trường"},
        {"name": "🏆-bảng-vàng", "category": "⚔️ GAME ZONE", "type": "text", "topic": "🏆 BXH"},
        {"name": "🎒-cửa-hàng", "category": "⚔️ GAME ZONE", "type": "text", "topic": "🛒 Shop"},
        {"name": "🔊 Game Voice", "category": "⚔️ GAME ZONE", "type": "voice"},
        # Mini games
        {"name": "🎲-xúc-xắc", "category": "🎲 MINI GAMES", "type": "text", "topic": "🎲 Xúc xắc / đồng xu"},
        {"name": "🎰-slot-machine", "category": "🎲 MINI GAMES", "type": "text", "topic": "🎰 Máy đánh bạc"},
        {"name": "🃏-blackjack", "category": "🎲 MINI GAMES", "type": "text", "topic": "🃏 Blackjack 21"},
        {"name": "💣-minesweeper", "category": "🎲 MINI GAMES", "type": "text", "topic": "💣 Dò mìn"},
        {"name": "🎯-bắn-cung", "category": "🎲 MINI GAMES", "type": "text", "topic": "🎯 Bắn cung"},
        # NSFW zone
        {"name": "🔞-xác-nhận-18", "category": "🔞 NSFW ZONE", "type": "text", "topic": "Xác nhận 18+", "nsfw": False},
        {"name": "🔞-nsfw-18", "category": "🔞 NSFW ZONE", "type": "text", "topic": "🔞 NSFW Content", "nsfw": True},
        {"name": "🔞-chat-18", "category": "🔞 NSFW ZONE", "type": "text", "topic": "💬 Chat 18+", "nsfw": False},
        {"name": "🔊 NSFW Voice", "category": "🔞 NSFW ZONE", "type": "voice", "nsfw": False},
        # Staff only
        {"name": "🛡️-staff-chat", "category": "🛡️ STAFF ONLY", "type": "text", "topic": "🛡️ Staff only"},
        {"name": "📊-bot-logs", "category": "🛡️ STAFF ONLY", "type": "text", "topic": "📊 Bot logs"},
        {"name": "🔊 Staff Voice", "category": "🛡️ STAFF ONLY", "type": "voice"},
    ],
}

# ============================================================
# GAME DATA
# ============================================================
CLASSES = {
    "warrior": {"name":"⚔️ Chiến Binh","hp":150,"atk":20,"def":10,"skill":"Chém Mạnh","emoji":"⚔️","crit":10},
    "mage": {"name":"🔮 Pháp Sư","hp":100,"atk":30,"def":5,"skill":"Cầu Lửa","emoji":"🔮","crit":15},
    "archer": {"name":"🏹 Cung Thủ","hp":120,"atk":25,"def":7,"skill":"Tên Độc","emoji":"🏹","crit":20},
    "assassin": {"name":"🗡️ Sát Thủ","hp":110,"atk":35,"def":3,"skill":"Đâm Lén","emoji":"🗡️","crit":25},
    "tank": {"name":"🛡️ Tank","hp":200,"atk":10,"def":20,"skill":"Khiên Thép","emoji":"🛡️","crit":5},
}
ITEMS = [
    {"name":"Kiếm Sắt","type":"weapon","atk":10,"price":100,"emoji":"🗡️"},
    {"name":"Kiếm Vàng","type":"weapon","atk":25,"price":300,"emoji":"⚔️"},
    {"name":"Giáp Da","type":"armor","def":8,"price":100,"emoji":"🛡️"},
    {"name":"Giáp Sắt","type":"armor","def":20,"price":300,"emoji":"🛡️"},
    {"name":"Nhẫn Lửa","type":"ring","atk":15,"price":500,"emoji":"💍"},
    {"name":"Bùa Hộ Mệnh","type":"amulet","hp":50,"price":400,"emoji":"📿"},
    {"name":"Giày Bay","type":"boots","spd":10,"price":350,"emoji":"👢"},
    {"name":"Mũ Phù Thủy","type":"helmet","def":12,"price":250,"emoji":"🎩"},
]
WC_TEAMS = ["🇧🇷 Brazil","🇦🇷 Argentina","🇫🇷 Pháp","🇩🇪 Đức","🇪🇸 Tây Ban Nha","🇵🇹 Bồ Đào Nha","🇬🇧 Anh","🇳🇱 Hà Lan","🇮🇹 Ý","🇧🇪 Bỉ","🇺🇾 Uruguay","🇭🇷 Croatia","🇲🇦 Ma Rốc","🇯🇵 Nhật Bản","🇰🇷 Hàn Quốc","🇸🇳 Senegal"]

# ============================================================
# HELPERS
# ============================================================
def create_embed(title, description="", color=discord.Color.blue(), fields=None, thumbnail=None, image=None, footer=None, timestamp=False):
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now() if timestamp else None)
    if fields:
        for f in fields: embed.add_field(name=f.get("name",""), value=f.get("value",""), inline=f.get("inline",True))
    if thumbnail: embed.set_thumbnail(url=thumbnail)
    if image: embed.set_image(url=image)
    if footer: embed.set_footer(text=footer)
    return embed

def check_token(uid): return user_tokens.get(uid)
def check_player(uid): return players.get(uid)

async def async_request(url, headers=None, json_data=None, method="GET"):
    async with aiohttp.ClientSession() as session:
        try:
            if method == "GET":
                async with session.get(url, headers=headers, timeout=10) as resp:
                    return await resp.json() if resp.status == 200 else None
            elif method == "POST":
                async with session.post(url, headers=headers, json=json_data, timeout=10) as resp:
                    return await resp.json() if resp.status == 200 else None
            elif method == "PATCH":
                async with session.patch(url, headers=headers, json=json_data, timeout=10) as resp:
                    return {"status": resp.status}
        except: return None

# ============================================================
# NSFW HELPERS (GIỮ TỪ TOOL CŨ)
# ============================================================
async def scrape_anhanime4k():
    images=[]
    try:
        async with aiohttp.ClientSession() as session:
            page=random.randint(1,20)
            url=f"https://anhanime4k.com/hentai/page/{page}/" if page>1 else "https://anhanime4k.com/hentai/"
            async with session.get(url, headers={**HEADERS_WEB,"Referer":"https://anhanime4k.com/"}, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status==200:
                    html=await resp.text()
                    soup=BeautifulSoup(html,'lxml')
                    for img in soup.find_all('img'):
                        src=img.get('src') or img.get('data-src')
                        if src and ('wp-content' in src or 'uploads' in src):
                            if src.startswith('//'): src='https:'+src
                            if src.startswith('http') and any(e in src.lower() for e in ['.jpg','.png','.gif']): images.append(src)
    except Exception as e: print(f"[SCRAPE] {e}")
    return list(set(images))

async def scrape_quatvn():
    images=[]
    try:
        async with aiohttp.ClientSession() as session:
            for endpoint in ["https://quatvn.biz/","https://quatvn.biz/wp-json/wp/v2/media?per_page=20"]:
                try:
                    async with session.get(endpoint, headers={**HEADERS_WEB,"Referer":"https://quatvn.biz/"}, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                        if resp.status==200:
                            ct=resp.headers.get('Content-Type','')
                            if 'application/json' in ct:
                                data=await resp.json()
                                for item in data:
                                    if 'source_url' in item: images.append(item['source_url'])
                            else:
                                html=await resp.text()
                                soup=BeautifulSoup(html,'lxml')
                                for img in soup.find_all('img'):
                                    src=img.get('src') or img.get('data-src')
                                    if src and src.startswith('http'): images.append(src)
                except: pass
    except Exception as e: print(f"[SCRAPE] {e}")
    return list(set(images))

async def get_web_nsfw_url(category):
    cache_key="hentai" if category=="hentai" else "quatvn"
    if cache_key in nsfw_web_cache and cache_key in cache_timestamp:
        if time.time()-cache_timestamp[cache_key]<300:
            if nsfw_web_cache[cache_key]: return random.choice(nsfw_web_cache[cache_key])
    images=await scrape_anhanime4k() if category=="hentai" else await scrape_quatvn()
    if images:
        nsfw_web_cache[cache_key]=images
        cache_timestamp[cache_key]=time.time()
        return random.choice(images)
    return None

def get_local_nsfw_file(category):
    cat_dir=NSFW_CATEGORIES.get(category, os_module.path.join(NSFW_DIR,"waifu"))
    files=[]
    for ext in ["*.jpg","*.jpeg","*.png","*.gif","*.webp"]:
        files.extend(glob.glob(os_module.path.join(cat_dir,ext)))
    if files:
        fp=random.choice(files)
        return discord.File(fp), os_module.path.basename(fp)
    return None, None

# ============================================================
# BLACKJACK HELPERS
# ============================================================
def create_deck():
    deck = []
    for suit in CARD_SUITS:
        for name in CARD_NAMES:
            deck.append({"name": name, "suit": suit, "value": CARD_VALUES[name]})
    random.shuffle(deck)
    return deck

def calculate_hand(hand):
    total = sum(card["value"] for card in hand)
    aces = sum(1 for card in hand if card["name"] == "A")
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total

def hand_to_str(hand):
    return " | ".join([f"{card['name']}{card['suit']}" for card in hand])

# ============================================================
# EVENTS
# ============================================================
@bot.event
async def on_ready():
    print(f"\033[92m✅ Bot Online: {bot.user}\033[0m")
    print(f"\033[96m✅ Servers: {len(bot.guilds)} | Users: {len(bot.users)}\033[0m")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/help | v5.0 FULL"))
    try:
        synced = await bot.tree.sync()
        print(f"\033[93m✅ Synced {len(synced)} commands\033[0m")
    except Exception as e:
        print(f"\033[91m❌ Sync error: {e}\033[0m")

# ============================================================
# HELP
# ============================================================
@bot.tree.command(name="help", description="📋 Menu chính")
async def help_command(interaction: discord.Interaction):
    embed = create_embed(
        title="🤖 DISCORD ALL-IN-ONE BOT v5.0",
        description="**Auto Setup + Game PvP + Mini Games + NSFW**\n━━━━━━━━━━━━━━━━━━━━━━",
        color=discord.Color.purple(),
        fields=[
            {"name": "🚀 **Auto Setup**", "value": "`/autosetup` - Tạo toàn bộ server\n`/autosetup YES` - Xác nhận xóa cũ", "inline": False},
            {"name": "👤 **Profile**", "value": "`/settoken` `/activity` `/spotify` `/avatar`", "inline": False},
            {"name": "⚔️ **Game PvP**", "value": "`/create` `/profile` `/battle` `/shop` `/buy` `/leaderboard` `/daily`", "inline": False},
            {"name": "🏆 **World Cup**", "value": "`/wc schedule` `/wc results` `/wc upcoming`", "inline": False},
            {"name": "🎲 **Mini Games**", "value": "`/slot` `/blackjack` `/minesweeper` `/archery`", "inline": False},
            {"name": "🔞 **NSFW (18+)**", "value": "`/nsfw waifu` `/nsfw neko` `/nsfw hentai` `/nsfw boobs` `/nsfw list`", "inline": False},
            {"name": "📊 **Thông Tin**", "value": "`/serverinfo` `/userinfo` `/avataruser`", "inline": False},
            {"name": "💬 **Chat Tools**", "value": "`/spam` `/say` `/embed` `/clear`", "inline": False},
            {"name": "😂 **Fun**", "value": "`/meme` `/dice` `/coin` `/8ball` `/fact` `/hack` `/kill` `/hug` `/slap` `/ship` `/iq` `/gay`", "inline": False},
        ],
        footer="v5.0 FULL - NSFW + Auto Setup + All Games"
    )
    await interaction.response.send_message(embed=embed)

# ============================================================
# NSFW COMMAND (18+) - GIỮ NGUYÊN TỪ TOOL CŨ
# ============================================================
@bot.tree.command(name="nsfw", description="🔞 NSFW content (18+)")
@app_commands.describe(category="Thể loại")
@app_commands.choices(category=[
    app_commands.Choice(name="👧 Waifu", value="waifu"),
    app_commands.Choice(name="🐱 Neko", value="neko"),
    app_commands.Choice(name="👤 Trap", value="trap"),
    app_commands.Choice(name="🍆 Blowjob", value="blowjob"),
    app_commands.Choice(name="📚 Hentai", value="hentai"),
    app_commands.Choice(name="🍒 Boobs", value="boobs"),
    app_commands.Choice(name="🌸 Pussy", value="pussy"),
    app_commands.Choice(name="🍑 Anal", value="anal"),
    app_commands.Choice(name="🔞 Gonewild", value="gonewild"),
    app_commands.Choice(name="📋 Danh sách", value="list"),
])
async def nsfw_command(interaction: discord.Interaction, category: str = "waifu"):
    # Kiểm tra kênh NSFW
    if isinstance(interaction.channel, discord.TextChannel) and not interaction.channel.is_nsfw():
        await interaction.response.send_message("🔞 Chỉ dùng trong kênh NSFW!", ephemeral=True)
        return

    if category == "list":
        list_embed = create_embed(
            title="🔞 DANH SÁCH NSFW",
            description="Tất cả thể loại:",
            color=discord.Color.dark_red(),
            fields=[
                {"name": "👧 Waifu", "value": "Ảnh waifu 18+", "inline": True},
                {"name": "🐱 Neko", "value": "Neko girls", "inline": True},
                {"name": "👤 Trap", "value": "Traps", "inline": True},
                {"name": "🍆 Blowjob", "value": "Oral", "inline": True},
                {"name": "📚 Hentai", "value": "Truyện tranh", "inline": True},
                {"name": "🍒 Boobs", "value": "Ngực", "inline": True},
                {"name": "🌸 Pussy", "value": "Phần nhạy cảm", "inline": True},
                {"name": "🍑 Anal", "value": "Hậu môn", "inline": True},
                {"name": "🔞 Gonewild", "value": "Ảnh thật", "inline": True},
            ]
        )
        await interaction.response.send_message(embed=list_embed)
        return

    await interaction.response.defer()
    
    # Thử scrape web trước
    image_url = await get_web_nsfw_url(category)
    if image_url:
        embed = create_embed(
            title=f"🔞 {category.upper()}",
            description=f"Yêu cầu bởi {interaction.user.mention}",
            color=discord.Color.dark_red(),
            image=image_url,
            footer="NSFW Content | 18+ Only"
        )
        await interaction.followup.send(embed=embed)
        return

    # Fallback local
    file, filename = get_local_nsfw_file(category)
    if file:
        embed = create_embed(
            title=f"🔞 {category.upper()}",
            description=f"Local: {filename}",
            color=discord.Color.dark_red(),
            footer="NSFW Content | 18+ Only"
        )
        await interaction.followup.send(embed=embed, file=file)
    else:
        await interaction.followup.send("❌ Không có ảnh trong bộ nhớ!")

# ============================================================
# AUTO SETUP (FULL - CÓ NSFW ZONE + XÁC NHẬN 18+)
# ============================================================
@bot.tree.command(name="autosetup", description="🚀 Tự động tạo toàn bộ server (game + mini games + nsfw)")
@app_commands.describe(confirm="Gõ 'YES' để xác nhận (sẽ xóa cấu trúc cũ)")
@app_commands.default_permissions(administrator=True)
async def autosetup_command(interaction: discord.Interaction, confirm: str = "NO"):
    if confirm.upper() != "YES":
        await interaction.response.send_message(
            embed=create_embed(
                title="⚠️ XÁC NHẬN AUTO SETUP",
                description="Lệnh này sẽ **XÓA TẤT CẢ** kênh, role, category hiện tại và tạo mới.\n"
                            "Bao gồm: Game Zone, Mini Games, NSFW Zone.\n"
                            "Dùng `/autosetup YES` để xác nhận.",
                color=discord.Color.orange(),
            ),
            ephemeral=True,
        )
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ Chỉ dùng trong server!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    status_msgs = []
    bot_member = guild.me
    bot_top_role = bot_member.top_role.position

    try:
        # Xóa kênh cũ
        status_msgs.append("🗑️ Đang xóa kênh cũ...")
        await interaction.followup.send("\n".join(status_msgs), ephemeral=True)
        for channel in guild.channels:
            try: await channel.delete(reason="Auto setup")
            except: pass

        # Xóa role cũ
        status_msgs.append("🗑️ Đang xóa role cũ...")
        await interaction.followup.send("\n".join(status_msgs), ephemeral=True)
        for role in guild.roles:
            if role.name == "@everyone" or role.managed or role >= bot_top_role: continue
            try: await role.delete(reason="Auto setup")
            except: pass

        # Tạo roles
        status_msgs.append("👑 Đang tạo roles...")
        await interaction.followup.send("\n".join(status_msgs), ephemeral=True)
        created_roles = {}
        for rc in AUTO_SERVER_CONFIG["roles"]:
            try:
                perms = discord.Permissions()
                for pn in rc.get("permissions", []):
                    try: setattr(perms, pn, True)
                    except: pass
                nr = await guild.create_role(name=rc["name"], color=discord.Color(rc["color"]), permissions=perms, hoist=rc.get("hoist", False), mentionable=True, reason="Auto setup")
                created_roles[rc["name"]] = nr
                status_msgs.append(f"  ✅ {rc['name']}")
            except Exception as e:
                status_msgs.append(f"  ❌ {rc['name']}: {e}")

        # Tạo categories với phân quyền NSFW
        status_msgs.append("📁 Đang tạo categories...")
        await interaction.followup.send("\n".join(status_msgs), ephemeral=True)
        created_categories = {}
        
        nsfw_role = created_roles.get("🔞 NSFW Access")
        admin_role = created_roles.get("👑 Admin")
        mod_role = created_roles.get("🛡️ Mod")
        
        for cc in AUTO_SERVER_CONFIG["categories"]:
            try:
                overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)}
                
                # NSFW Zone - chỉ role NSFW mới thấy
                if "NSFW" in cc["name"].upper():
                    overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False, connect=False)
                    if nsfw_role:
                        overwrites[nsfw_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)
                    if admin_role:
                        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)
                
                # Staff only
                if "STAFF" in cc["name"].upper():
                    overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False, connect=False)
                    if admin_role: overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)
                    if mod_role: overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)
                
                nc = await guild.create_category(name=cc["name"], overwrites=overwrites, reason="Auto setup")
                created_categories[cc["name"]] = nc
                status_msgs.append(f"  ✅ {cc['name']}")
            except Exception as e:
                status_msgs.append(f"  ❌ {cc['name']}: {e}")

        # Tạo channels
        status_msgs.append("📺 Đang tạo channels...")
        await interaction.followup.send("\n".join(status_msgs), ephemeral=True)
        created_channels = {}
        
        for ch in AUTO_SERVER_CONFIG["channels"]:
            try:
                cat = created_categories.get(ch["category"])
                if not cat: continue
                
                overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)}
                
                # Phân quyền NSFW
                if "NSFW" in ch["category"].upper():
                    overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False, connect=False)
                    if nsfw_role: overwrites[nsfw_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)
                    if admin_role: overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)
                
                # Staff
                if "STAFF" in ch["category"].upper():
                    overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False, connect=False)
                    if admin_role: overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)
                    if mod_role: overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True)
                
                if ch["type"] == "text":
                    nc = await guild.create_text_channel(name=ch["name"], category=cat, topic=ch.get("topic", ""), nsfw=ch.get("nsfw", False), overwrites=overwrites, reason="Auto setup")
                else:
                    nc = await guild.create_voice_channel(name=ch["name"], category=cat, overwrites=overwrites, reason="Auto setup")
                created_channels[ch["name"]] = nc
                status_msgs.append(f"  ✅ {ch['type']}: {ch['name']}")
            except Exception as e:
                status_msgs.append(f"  ❌ {ch['name']}: {e}")

        # Welcome message
        wc = created_channels.get("👋-chào-mừng")
        if wc:
            rembed = create_embed(
                title="📜 LUẬT LỆ SERVER",
                description="Chào mừng! Vui lòng đọc luật:",
                color=discord.Color.red(),
                fields=[
                    {"name": "1️⃣ Tôn trọng", "value": "Không xúc phạm thành viên khác", "inline": False},
                    {"name": "2️⃣ Spam", "value": "Spam ở kênh spam-chill", "inline": False},
                    {"name": "3️⃣ NSFW", "value": "Nội dung 18+ chỉ trong khu vực NSFW, cần role 🔞 NSFW Access", "inline": False},
                    {"name": "4️⃣ Game", "value": "Chơi game vui vẻ, không cheat", "inline": False},
                    {"name": "5️⃣ Staff", "value": "Tuân theo Admin và Mod", "inline": False},
                ],
                footer="✅ React 👍 để xác nhận"
            )
            rm = await wc.send(embed=rembed)
            await rm.add_reaction("👍")

        # NSFW xác nhận 18+
        verify_ch = created_channels.get("🔞-xác-nhận-18")
        if verify_ch and nsfw_role:
            try: await verify_ch.purge(limit=10)
            except: pass
            
            class VerifyView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)
                
                @discord.ui.button(label="✅ Tôi trên 18 tuổi", style=discord.ButtonStyle.green, custom_id="verify_18")
                async def verify_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    role = discord.utils.get(button_interaction.guild.roles, name="🔞 NSFW Access")
                    if role and role not in button_interaction.user.roles:
                        try:
                            await button_interaction.user.add_roles(role)
                            await button_interaction.response.send_message("✅ Đã xác nhận! Bạn có thể truy cập khu vực NSFW.", ephemeral=True)
                        except:
                            await button_interaction.response.send_message("❌ Lỗi! Liên hệ Admin.", ephemeral=True)
                    else:
                        await button_interaction.response.send_message("✅ Bạn đã xác nhận rồi!", ephemeral=True)
            
            verify_embed = create_embed(
                title="🔞 XÁC NHẬN 18+",
                description="Nhấn nút bên dưới để xác nhận bạn **trên 18 tuổi**.\n"
                            "Sau khi xác nhận, bạn sẽ nhận role <@&{0}> và truy cập được khu vực NSFW.".format(nsfw_role.id),
                color=discord.Color.dark_red(),
                footer="Bạn phải trên 18 tuổi để tiếp tục!"
            )
            await verify_ch.send(embed=verify_embed, view=VerifyView())

        # NSFW content channel welcome
        nsfw_ch = created_channels.get("🔞-nsfw-18")
        if nsfw_ch:
            try: await nsfw_ch.purge(limit=10)
            except: pass
            nsfw_welcome = create_embed(
                title="🔞 KÊNH NSFW",
                description="Dùng lệnh:\n"
                            "`/nsfw waifu` - Ảnh waifu\n"
                            "`/nsfw neko` - Neko girls\n"
                            "`/nsfw hentai` - Hentai\n"
                            "`/nsfw boobs` - Ngực\n"
                            "`/nsfw pussy` - Phần nhạy cảm\n"
                            "`/nsfw anal` - Hậu môn\n"
                            "`/nsfw blowjob` - Oral\n"
                            "`/nsfw gonewild` - Ảnh thật\n"
                            "`/nsfw list` - Danh sách",
                color=discord.Color.dark_purple(),
                footer="🔞 18+ Only | NSFW Content"
            )
            await nsfw_ch.send(embed=nsfw_welcome)

        # NSFW chat welcome
        chat_ch = created_channels.get("🔞-chat-18")
        if chat_ch:
            try: await chat_ch.purge(limit=10)
            except: pass
            await chat_ch.send(embed=create_embed(title="💬 CHAT 18+", description="Chào mừng đến khu vực chat 18+!", color=discord.Color.gold()))

        status_msgs.append(f"\n✅ **HOÀN TẤT!** {len(created_roles)} roles, {len(created_categories)} categories, {len(created_channels)} channels")
        status_msgs.append("🔞 NSFW Zone đã sẵn sàng với xác nhận 18+!")
        await interaction.followup.send("\n".join(status_msgs), ephemeral=True)

        # Log
        log_ch = created_channels.get("📊-bot-logs")
        if log_ch:
            await log_ch.send(embed=create_embed(
                title="🚀 AUTO SETUP HOÀN TẤT",
                description=f"Bởi: {interaction.user.mention}",
                color=discord.Color.green(),
                fields=[
                    {"name":"👑 Roles","value":str(len(created_roles)),"inline":True},
                    {"name":"📁 Categories","value":str(len(created_categories)),"inline":True},
                    {"name":"📺 Channels","value":str(len(created_channels)),"inline":True},
                    {"name":"🔞 NSFW","value":"Đã bật","inline":True},
                ],
                timestamp=True
            ))

    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)

# ============================================================
# PROFILE COMMANDS
# ============================================================
@bot.tree.command(name="settoken", description="🔑 Lưu User Token")
@app_commands.describe(token="Token Discord")
async def settoken_command(interaction: discord.Interaction, token: str):
    data = await async_request("https://discord.com/api/v9/users/@me", headers={"Authorization": token})
    if data and "username" in data:
        user_tokens[interaction.user.id] = token
        await interaction.response.send_message(embed=create_embed(title="✅ Token Đã Lưu!", description=f"**{data['username']}**", color=discord.Color.green()), ephemeral=True)
    else:
        await interaction.response.send_message("❌ Token không hợp lệ!", ephemeral=True)

@bot.tree.command(name="activity", description="🎮 Fake Activity")
@app_commands.describe(name="Tên", details="Chi tiết", state="Trạng thái", type="Loại", image_url="URL ảnh")
@app_commands.choices(type=[app_commands.Choice(name="🎮 Playing", value="0"),app_commands.Choice(name="📺 Streaming", value="1"),app_commands.Choice(name="🎵 Listening", value="2"),app_commands.Choice(name="👀 Watching", value="3"),app_commands.Choice(name="🏆 Competing", value="5")])
async def activity_command(interaction: discord.Interaction, name: str="I'm sleeping", details: str="Zzz...", state: str="Don't disturb", type: str="0", image_url: Optional[str]=None):
    token = check_token(interaction.user.id)
    if not token: await interaction.response.send_message("❌ `/settoken`!", ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    try:
        import websocket as ws_module
        sp = base64.b64encode(json.dumps({"os":"Windows","browser":"Discord Client","release_channel":"stable","client_version":"1.0.9182","os_version":"10.0.26100","os_arch":"x64","app_arch":"x64","system_locale":"en-US","browser_user_agent":"Mozilla/5.0 discord/1.0.9182","browser_version":"33.3.2","client_build_number":504649,"native_build_number":59498,"client_event_source":None}).encode()).decode()
        ws = ws_module.WebSocket(); ws.connect("wss://gateway.discord.gg/?v=9&encoding=json"); json.loads(ws.recv())
        ws.send(json.dumps({"op":2,"d":{"token":token,"capabilities":16381,"properties":json.loads(base64.b64decode(sp).decode())}})); json.loads(ws.recv())
        act = {"name":name,"type":int(type),"details":details,"state":state,"timestamps":{"start":int(time.time()*1000)}}
        if image_url: act["assets"] = {"large_image":f"mp:{image_url}","large_text":name}
        if int(type)==1: act["url"]="https://twitch.tv/discord"
        ws.send(json.dumps({"op":3,"d":{"since":None,"activities":[act],"status":"online","afk":False}})); ws.close()
        await interaction.followup.send(f"✅ Activity: {name}", ephemeral=True)
    except Exception as e: await interaction.followup.send(f"❌ {e}", ephemeral=True)

@bot.tree.command(name="spotify", description="🎵 Fake Spotify")
@app_commands.describe(song="Tên bài", artist="Ca sĩ", album="Album", image_url="URL ảnh")
async def spotify_command(interaction: discord.Interaction, song: str="Nhạc Chill", artist: str="Various", album: str="Top Hits", image_url: Optional[str]=None):
    token = check_token(interaction.user.id)
    if not token: await interaction.response.send_message("❌ `/settoken`!", ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    try:
        import websocket as ws_module
        sp = base64.b64encode(json.dumps({"os":"Windows","browser":"Discord Client","release_channel":"stable","client_version":"1.0.9182","os_version":"10.0.26100","os_arch":"x64","app_arch":"x64","system_locale":"en-US","browser_user_agent":"Mozilla/5.0 discord/1.0.9182","browser_version":"33.3.2","client_build_number":504649,"native_build_number":59498,"client_event_source":None}).encode()).decode()
        ws = ws_module.WebSocket(); ws.connect("wss://gateway.discord.gg/?v=9&encoding=json"); json.loads(ws.recv())
        ws.send(json.dumps({"op":2,"d":{"token":token,"capabilities":16381,"properties":json.loads(base64.b64decode(sp).decode())}})); json.loads(ws.recv())
        sact = {"name":"Spotify","type":2,"details":song,"state":artist,"timestamps":{"start":int(time.time()*1000),"end":int((time.time()+180)*1000)},"assets":{"large_image":f"mp:{image_url}" if image_url else "spotify:ab67616d0000b273","large_text":album}}
        ws.send(json.dumps({"op":3,"d":{"since":None,"activities":[sact],"status":"online","afk":False}})); ws.close()
        await interaction.followup.send(f"✅ Spotify: {song}", ephemeral=True)
    except Exception as e: await interaction.followup.send(f"❌ {e}", ephemeral=True)

@bot.tree.command(name="avatar", description="🖼️ Xem avatar")
@app_commands.describe(user="Người dùng")
async def avatar_command(interaction: discord.Interaction, user: discord.User=None):
    u = user or interaction.user
    await interaction.response.send_message(embed=create_embed(title=f"🖼️ {u.name}", image=u.display_avatar.url, color=discord.Color.blue()))

# ============================================================
# GAME COMMANDS
# ============================================================
@bot.tree.command(name="create", description="⚔️ Tạo nhân vật")
@app_commands.describe(name="Tên", class_name="Nghề")
@app_commands.choices(class_name=[app_commands.Choice(name=v["name"], value=k) for k,v in CLASSES.items()])
async def create_character(interaction: discord.Interaction, name: str, class_name: str):
    uid = interaction.user.id
    if uid in players: await interaction.response.send_message("❌ Đã có nhân vật!", ephemeral=True); return
    cls = CLASSES[class_name]
    players[uid] = {"name":name,"class":class_name,"level":1,"xp":0,"hp":cls["hp"],"max_hp":cls["hp"],"atk":cls["atk"],"def":cls["def"],"gold":100,"skill":cls["skill"],"crit":cls["crit"],"inventory":[],"wins":0,"losses":0,"daily":None}
    embed = create_embed(title=f"✅ {cls['emoji']} {name}", color=discord.Color.green(), fields=[{"name":"Nghề","value":cls['name'],"inline":True},{"name":"HP","value":str(cls['hp']),"inline":True},{"name":"ATK","value":str(cls['atk']),"inline":True},{"name":"DEF","value":str(cls['def']),"inline":True},{"name":"Gold","value":"100","inline":True}])
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="profile", description="📊 Xem thông tin")
async def view_profile(interaction: discord.Interaction):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ `/create`!", ephemeral=True); return
    cls = CLASSES[p["class"]]
    total = p['wins']+p['losses']
    wr = (p['wins']/total*100) if total>0 else 0
    embed = create_embed(title=f"{cls['emoji']} {p['name']} - Lv.{p['level']}", color=discord.Color.blue(), fields=[{"name":"HP","value":f"{p['hp']}/{p['max_hp']}","inline":True},{"name":"ATK","value":str(p['atk']),"inline":True},{"name":"DEF","value":str(p['def']),"inline":True},{"name":"Gold","value":str(p['gold']),"inline":True},{"name":"XP","value":f"{p['xp']}/100","inline":True},{"name":"W/L","value":f"{p['wins']}/{p['losses']} ({wr:.1f}%)","inline":True}])
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="battle", description="⚔️ PvP")
async def battle_command(interaction: discord.Interaction):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ `/create`!", ephemeral=True); return
    opponents = [pp for pid,pp in players.items() if pid != interaction.user.id]
    await interaction.response.defer(); await asyncio.sleep(1.5)
    if opponents:
        opp = random.choice(opponents); opp_name = opp['name']
        p_crit = random.random()*100 < p['crit']; o_crit = random.random()*100 < opp['crit']
        p_pow = p['atk']+p['def']+random.randint(-10,20); o_pow = opp['atk']+opp['def']+random.randint(-10,20)
        if p_crit: p_pow*=1.5
        if o_crit: o_pow*=1.5
        result = p_pow > o_pow
        if result: g=random.randint(30,100); x=random.randint(20,50); p['wins']+=1; opp['losses']+=1
        else: g=random.randint(5,20); x=random.randint(5,10); p['losses']+=1; opp['wins']+=1
    else:
        opp_name="BOT"; result=random.random()<0.55; g=random.randint(20,50); x=random.randint(10,30)
    p['gold']+=g; p['xp']+=x
    msg = f"⚔️ {'THẮNG' if result else 'THUA'} vs {opp_name}!\n+{g}💰 +{x}XP"
    if p['xp']>=100: p['level']+=1; p['xp']-=100; p['max_hp']+=20; p['hp']=p['max_hp']; p['atk']+=random.randint(3,7); p['def']+=random.randint(2,5); msg+=f"\n🎉 LEVEL UP! Lv.{p['level']}!"
    await interaction.followup.send(msg)

@bot.tree.command(name="shop", description="🛒 Cửa hàng")
async def shop_command(interaction: discord.Interaction):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ `/create`!", ephemeral=True); return
    items = "\n".join([f"{i['emoji']} **{i['name']}** - {i['price']}💰 | +{i.get('atk',i.get('def',i.get('hp',i.get('spd',0))))} {list(i.keys())[2]}" for i in ITEMS])
    await interaction.response.send_message(embed=create_embed(title="🛒 CỬA HÀNG", description=f"💰 Số dư: **{p['gold']}**\n\n{items}\n\nDùng `/buy <tên>`", color=discord.Color.gold()))

@bot.tree.command(name="buy", description="💰 Mua đồ")
@app_commands.describe(item_name="Tên đồ")
async def buy_command(interaction: discord.Interaction, item_name: str):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ `/create`!", ephemeral=True); return
    item = next((i for i in ITEMS if i['name'].lower()==item_name.lower()), None)
    if not item: await interaction.response.send_message("❌ Không tìm thấy!"); return
    if p['gold']<item['price']: await interaction.response.send_message(f"❌ Thiếu {item['price']-p['gold']}💰!"); return
    p['gold']-=item['price']; p['inventory'].append(item)
    for k in ['atk','def','hp','spd']:
        if k in item: p['atk' if k=='atk' else 'def' if k=='def' else 'max_hp' if k=='hp' else 'spd']+=item[k]
    if 'hp' in item: p['hp']+=item['hp']
    await interaction.response.send_message(f"✅ Đã mua {item['emoji']} **{item['name']}**!")

@bot.tree.command(name="leaderboard", description="🏆 BXH")
async def leaderboard_command(interaction: discord.Interaction):
    if not players: await interaction.response.send_message("❌ Chưa có ai!"); return
    sorted_p = sorted(players.items(), key=lambda x: (x[1]['wins'], x[1]['level']), reverse=True)[:10]
    lb = "\n".join([f"**{i+1}.** {CLASSES[p[1]['class']]['emoji']} {p[1]['name']} - Lv.{p[1]['level']} | {p[1]['wins']}W/{p[1]['losses']}L" for i,p in enumerate(sorted_p)])
    await interaction.response.send_message(embed=create_embed(title="🏆 BẢNG XẾP HẠNG", description=lb, color=discord.Color.gold()))

@bot.tree.command(name="daily", description="🎁 Nhận thưởng hàng ngày")
async def daily_command(interaction: discord.Interaction):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ `/create`!", ephemeral=True); return
    now = datetime.now()
    if p.get('daily') and (now - datetime.fromisoformat(p['daily'])) < timedelta(hours=24):
        rem = timedelta(hours=24) - (now - datetime.fromisoformat(p['daily']))
        await interaction.response.send_message(f"⏳ Đã nhận! Quay lại sau {rem.seconds//3600}h{(rem.seconds%3600)//60}m."); return
    gold_r = random.randint(50,150); p['gold']+=gold_r; p['daily']=now.isoformat()
    await interaction.response.send_message(f"🎁 Nhận **{gold_r}** gold!")

# ============================================================
# WORLD CUP
# ============================================================
@bot.tree.command(name="wc", description="🏆 World Cup")
@app_commands.describe(action="Chọn")
@app_commands.choices(action=[app_commands.Choice(name="📅 Lịch đấu", value="schedule"),app_commands.Choice(name="📊 Kết quả", value="results"),app_commands.Choice(name="🔜 Sắp diễn ra", value="upcoming")])
async def wc_command(interaction: discord.Interaction, action: str):
    if action == "schedule":
        matches = "\n".join([f"⚽ {random.choice(WC_TEAMS)} vs {random.choice(WC_TEAMS)} - {random.randint(1,31)}/12" for _ in range(5)])
        embed = create_embed(title="📅 LỊCH ĐẤU", description=matches, color=discord.Color.green())
    elif action == "results":
        results = "\n".join([f"⚽ {random.choice(WC_TEAMS)} {random.randint(0,5)}-{random.randint(0,5)} {random.choice(WC_TEAMS)}" for _ in range(5)])
        embed = create_embed(title="📊 KẾT QUẢ", description=results, color=discord.Color.blue())
    else:
        upc = "\n".join([f"🔜 {random.choice(WC_TEAMS)} vs {random.choice(WC_TEAMS)}" for _ in range(3)])
        embed = create_embed(title="🔜 SẮP DIỄN RA", description=upc, color=discord.Color.orange())
    await interaction.response.send_message(embed=embed)

# ============================================================
# INFO
# ============================================================
@bot.tree.command(name="serverinfo", description="📊 Thông tin server")
async def serverinfo_command(interaction: discord.Interaction):
    g = interaction.guild
    embed = create_embed(title=f"📊 {g.name}", description=f"**Owner:** {g.owner.mention}\n**ID:** {g.id}", color=discord.Color.blue(), fields=[{"name":"👥 Members","value":str(g.member_count),"inline":True},{"name":"📁 Channels","value":str(len(g.channels)),"inline":True},{"name":"🎭 Roles","value":str(len(g.roles)),"inline":True}], thumbnail=g.icon.url if g.icon else None)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="👤 Info user")
@app_commands.describe(user="Người dùng")
async def userinfo_command(interaction: discord.Interaction, user: discord.User=None):
    u = user or interaction.user
    await interaction.response.send_message(embed=create_embed(title=f"👤 {u.name}", color=discord.Color.blue(), fields=[{"name":"ID","value":str(u.id),"inline":True},{"name":"Tạo lúc","value":u.created_at.strftime("%d/%m/%Y"),"inline":True},{"name":"Bot","value":"Có" if u.bot else "Không","inline":True}], thumbnail=u.display_avatar.url))

@bot.tree.command(name="avataruser", description="🖼️ Avatar user")
@app_commands.describe(user="Người dùng")
async def avataruser_command(interaction: discord.Interaction, user: discord.User):
    await interaction.response.send_message(embed=create_embed(title=f"🖼️ {user.name}", image=user.display_avatar.url, color=discord.Color.blue()))

# ============================================================
# CHAT TOOLS
# ============================================================
@bot.tree.command(name="spam", description="💬 Spam")
@app_commands.describe(message="Nội dung", count="Số lần (max 20)")
async def spam_command(interaction: discord.Interaction, message: str, count: int=5):
    if count>20: count=20
    await interaction.response.send_message("✅ Đang spam...", ephemeral=True)
    for _ in range(count): await interaction.channel.send(message); await asyncio.sleep(0.5)

@bot.tree.command(name="say", description="🗣️ Bot nói")
@app_commands.describe(message="Nội dung")
async def say_command(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("✅", ephemeral=True); await interaction.channel.send(message)

@bot.tree.command(name="embed", description="📝 Tạo embed")
@app_commands.describe(title="Tiêu đề", description="Mô tả", color="Màu hex")
async def embed_command(interaction: discord.Interaction, title: str, description: str="", color: str="0000ff"):
    try: c = discord.Color(int(color, 16))
    except: c = discord.Color.blue()
    await interaction.response.send_message(embed=create_embed(title=title, description=description, color=c))

@bot.tree.command(name="clear", description="🗑️ Xóa tin nhắn")
@app_commands.describe(amount="Số lượng (1-100)")
@app_commands.default_permissions(manage_messages=True)
async def clear_command(interaction: discord.Interaction, amount: int=10):
    if amount<1: amount=1
    if amount>100: amount=100
    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ Đã xóa {len(deleted)} tin nhắn!", ephemeral=True)
    except:
        await interaction.followup.send("❌ Thiếu quyền!", ephemeral=True)

# ============================================================
# MINI GAMES: SLOT
# ============================================================
@bot.tree.command(name="slot", description="🎰 Quay máy đánh bạc")
@app_commands.describe(bet="Số gold cược")
async def slot_command(interaction: discord.Interaction, bet: int=10):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ Cần tạo nhân vật `/create`!", ephemeral=True); return
    if bet<5 or bet>1000: await interaction.response.send_message("❌ Cược 5-1000 gold!"); return
    if p["gold"]<bet: await interaction.response.send_message(f"❌ Bạn chỉ có {p['gold']} gold!"); return
    p["gold"]-=bet
    result=[random.choice(SLOT_SYMBOLS) for _ in range(3)]
    result_str=" | ".join(result); combo="".join(result)
    win_mult=SLOT_PAYOUTS.get(combo,0)
    if win_mult>0:
        wa=bet*(win_mult//10); p["gold"]+=wa; outcome=f"🎉 JACKPOT! +{wa} gold!"; color=discord.Color.gold()
    elif result[0]==result[1] or result[1]==result[2] or result[0]==result[2]:
        wa=bet*2; p["gold"]+=wa; outcome=f"✨ Cặp đôi! +{wa} gold!"; color=discord.Color.green()
    else: outcome=f"💸 Thua {bet} gold!"; color=discord.Color.red()
    await interaction.response.send_message(embed=create_embed(title="🎰 SLOT MACHINE", description=f"**{result_str}**\n\n{outcome}\n💰 Số dư: **{p['gold']}**", color=color))

# ============================================================
# MINI GAMES: BLACKJACK
# ============================================================
@bot.tree.command(name="blackjack", description="🃏 Blackjack 21 điểm")
@app_commands.describe(action="Hành động", bet="Cược")
@app_commands.choices(action=[app_commands.Choice(name="🎮 Chơi mới", value="new"),app_commands.Choice(name="👊 Rút (Hit)", value="hit"),app_commands.Choice(name="✋ Dừng (Stand)", value="stand")])
async def blackjack_command(interaction: discord.Interaction, action: str="new", bet: int=50):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ Cần `/create`!", ephemeral=True); return
    uid=interaction.user.id
    if action=="new":
        if bet<10 or bet>p["gold"]: await interaction.response.send_message(f"❌ Cược 10-{p['gold']} gold!"); return
        deck=create_deck(); ph=[deck.pop(),deck.pop()]; dh=[deck.pop(),deck.pop()]
        mini_game_players["blackjack"][uid]={"hand":ph,"dealer_hand":dh,"deck":deck,"bet":bet,"status":"playing"}
        p["gold"]-=bet; pt=calculate_hand(ph)
        if pt==21:
            mini_game_players["blackjack"][uid]["status"]="blackjack"; wa=int(bet*2.5); p["gold"]+=wa
            emb=create_embed(title="🃏 BLACKJACK!",description=f"**Bạn:** {hand_to_str(ph)} ({pt})\n**Cái:** {hand_to_str(dh)} ({calculate_hand(dh)})\n\n🎉 +{wa} gold!",color=discord.Color.gold())
            del mini_game_players["blackjack"][uid]
        else:
            emb=create_embed(title="🃏 BLACKJACK",description=f"**Bạn:** {hand_to_str(ph)} ({pt})\n**Cái:** {dh[0]['name']}{dh[0]['suit']} | ❓\n\n💰 Cược: {bet}\n`/blackjack hit` hoặc `/blackjack stand`",color=discord.Color.blue())
        await interaction.response.send_message(embed=emb)
    elif action=="hit":
        g=mini_game_players["blackjack"].get(uid)
        if not g or g["status"]!="playing": await interaction.response.send_message("❌ `/blackjack new`!"); return
        g["hand"].append(g["deck"].pop()); pt=calculate_hand(g["hand"])
        if pt>21:
            g["status"]="bust"
            emb=create_embed(title="🃏 BUST!",description=f"**Bạn:** {hand_to_str(g['hand'])} ({pt})\n**Cái:** {hand_to_str(g['dealer_hand'])} ({calculate_hand(g['dealer_hand'])})\n\n💀 Thua {g['bet']} gold!",color=discord.Color.red())
            del mini_game_players["blackjack"][uid]
        else:
            emb=create_embed(title="🃏 HIT",description=f"**Bạn:** {hand_to_str(g['hand'])} ({pt})\n**Cái:** {g['dealer_hand'][0]['name']}{g['dealer_hand'][0]['suit']} | ❓",color=discord.Color.blue())
        await interaction.response.send_message(embed=emb)
    elif action=="stand":
        g=mini_game_players["blackjack"].get(uid)
        if not g or g["status"]!="playing": await interaction.response.send_message("❌ `/blackjack new`!"); return
        while calculate_hand(g["dealer_hand"])<17: g["dealer_hand"].append(g["deck"].pop())
        pt=calculate_hand(g["hand"]); dt=calculate_hand(g["dealer_hand"])
        if dt>21: wa=g["bet"]*2; p["gold"]+=wa; r=f"🎉 Cái bust! +{wa} gold!"; c=discord.Color.green()
        elif pt>dt: wa=g["bet"]*2; p["gold"]+=wa; r=f"✨ Thắng +{wa} gold!"; c=discord.Color.green()
        elif pt==dt: p["gold"]+=g["bet"]; r=f"🤝 Hòa! Hoàn {g['bet']} gold!"; c=discord.Color.orange()
        else: r=f"💸 Thua {g['bet']} gold!"; c=discord.Color.red()
        await interaction.response.send_message(embed=create_embed(title="🃏 KẾT QUẢ",description=f"**Bạn:** {hand_to_str(g['hand'])} ({pt})\n**Cái:** {hand_to_str(g['dealer_hand'])} ({dt})\n\n{r}\n💰 Số dư: **{p['gold']}**",color=c))
        del mini_game_players["blackjack"][uid]

# ============================================================
# MINI GAMES: MINESWEEPER
# ============================================================
@bot.tree.command(name="minesweeper", description="💣 Dò mìn")
@app_commands.describe(action="Hành động", size="Kích thước", mines="Số mìn", row="Hàng", col="Cột")
@app_commands.choices(action=[app_commands.Choice(name="🆕 Ván mới", value="new"),app_commands.Choice(name="👆 Mở ô", value="reveal"),app_commands.Choice(name="🚩 Đặt cờ", value="flag")])
async def minesweeper_command(interaction: discord.Interaction, action: str="new", size: int=5, mines: int=3, row: int=0, col: int=0):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ Cần `/create`!", ephemeral=True); return
    uid=interaction.user.id
    if action=="new":
        if size<3 or size>8: await interaction.response.send_message("❌ Size 3-8!"); return
        if mines<1 or mines>=size*size: await interaction.response.send_message(f"❌ Mìn 1-{size*size-1}!"); return
        board=[[0]*size for _ in range(size)]
        for mr,mc in random.sample([(r,c) for r in range(size) for c in range(size)],mines): board[mr][mc]=-1
        for r in range(size):
            for c in range(size):
                if board[r][c]==-1: continue
                board[r][c]=sum(1 for dr in[-1,0,1] for dc in[-1,0,1] if 0<=r+dr<size and 0<=c+dc<size and board[r+dr][c+dc]==-1)
        mini_game_players["minesweeper"][uid]={"board":board,"revealed":[[False]*size for _ in range(size)],"flagged":[[False]*size for _ in range(size)],"size":size,"mines":mines,"status":"playing","bet":mines*10}
        d="\n".join(["⬜ "*size for _ in range(size)])
        await interaction.response.send_message(embed=create_embed(title="💣 MINESWEEPER",description=f"**{size}x{size} | {mines} mìn**\n\n{d}\nDùng `/minesweeper reveal` hoặc `flag`",color=discord.Color.dark_gray()))
    elif action=="reveal":
        g=mini_game_players["minesweeper"].get(uid)
        if not g or g["status"]!="playing": await interaction.response.send_message("❌ `/minesweeper new`!"); return
        s=g["size"]
        if row<0 or row>=s or col<0 or col>=s: await interaction.response.send_message(f"❌ 0-{s-1}!"); return
        if g["revealed"][row][col] or g["flagged"][row][col]: await interaction.response.send_message("❌ Ô đã mở/cờ!"); return
        g["revealed"][row][col]=True
        if g["board"][row][col]==-1:
            g["status"]="lost"; p["gold"]-=g["bet"]
            d="\n".join(["".join(["💣 " if g["board"][r][c]==-1 else (str(g["board"][r][c])+"️⃣ " if g["revealed"][r][c] else "⬜ ") for c in range(s)]) for r in range(s)])
            await interaction.response.send_message(embed=create_embed(title="💣 BOOM!",description=f"{d}\n💸 Th
