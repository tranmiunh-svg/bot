from flask import Flask
from threading import Thread
import os as os_module
import sys

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running 24/7!"
Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()

import discord
from discord.ext import commands
from discord import app_commands
import json, base64, time, random, asyncio, glob, aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from io import BytesIO
from bs4 import BeautifulSoup

BOT_TOKEN = os_module.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("❌ Chưa set BOT_TOKEN!")
    sys.exit(1)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

user_tokens = {}
players = {}

NSFW_DIR = "nsfw_images"
if not os_module.path.exists(NSFW_DIR): os_module.makedirs(NSFW_DIR)
NSFW_CATEGORIES = {k: os_module.path.join(NSFW_DIR, k) for k in ["waifu","neko","trap","blowjob","hentai","boobs","pussy","anal","gonewild"]}
for d in NSFW_CATEGORIES.values():
    if not os_module.path.exists(d): os_module.makedirs(d)

nsfw_web_cache = {}
cache_timestamp = {}
HEADERS_WEB = {"User-Agent": "Mozilla/5.0", "Accept-Language": "vi-VN,vi;q=0.9"}

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

AUTO_SERVER_CONFIG = {
    "roles": [
        {"name":"👑 Admin","color":0xff0000,"permissions":["administrator"],"hoist":True},
        {"name":"🛡️ Mod","color":0x00ff00,"permissions":["kick_members","ban_members","manage_messages"],"hoist":True},
        {"name":"💎 VIP","color":0xffd700,"permissions":[],"hoist":True},
        {"name":"🔞 NSFW Access","color":0xe91e63,"permissions":[],"hoist":True},
        {"name":"👤 Member","color":0x3498db,"permissions":[],"hoist":False},
    ],
    "categories": [
        {"name":"📢 THÔNG TIN"},
        {"name":"💬 CHAT"},
        {"name":"🔞 NSFW ZONE"},
    ],
    "channels": [
        {"name":"📜-luật","category":"📢 THÔNG TIN","type":"text","topic":"Nội quy"},
        {"name":"👋-welcome","category":"📢 THÔNG TIN","type":"text","topic":"Chào mừng"},
        {"name":"💬-chat-chung","category":"💬 CHAT","type":"text","topic":"Chat thoải mái"},
        {"name":"🔞-xác-nhận","category":"🔞 NSFW ZONE","type":"text","topic":"Xác nhận 18+","nsfw":False},
        {"name":"🔞-nsfw","category":"🔞 NSFW ZONE","type":"text","topic":"NSFW Content","nsfw":True},
        {"name":"🔞-chat","category":"🔞 NSFW ZONE","type":"text","topic":"Chat 18+","nsfw":False},
    ],
}

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

# ========== SCRAPE ==========
async def scrape_web(url, is_json=False):
    images = []
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=HEADERS_WEB, timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status == 200:
                    if is_json:
                        data = await r.json()
                        for item in data:
                            if 'source_url' in item: images.append(item['source_url'])
                    else:
                        html = await r.text()
                        soup = BeautifulSoup(html, 'lxml')
                        for img in soup.find_all('img'):
                            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                            if src and src.startswith('http') and any(e in src.lower() for e in ['.jpg','.png','.gif','.webp']):
                                images.append(src)
    except: pass
    return list(set(images))

async def get_web_nsfw_url(category):
    if category in nsfw_web_cache and time.time() - cache_timestamp.get(category, 0) < 300:
        if nsfw_web_cache[category]: return random.choice(nsfw_web_cache[category])
    images = []
    # Nguồn 1: waifu.pics
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.waifu.pics/nsfw/{category}", timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 200:
                    d = await r.json()
                    if d.get("url"): images.append(d["url"])
    except: pass
    # Nguồn 2: quatvn.biz
    if not images: images = await scrape_web("https://quatvn.biz/wp-json/wp/v2/media?per_page=30", is_json=True)
    # Nguồn 3: damconuong.mom
    if not images: images = await scrape_web("https://damconuong.mom/")
    # Nguồn 4: anhanime4k (cho hentai)
    if not images and category == "hentai": images = await scrape_web(f"https://anhanime4k.com/hentai/page/{random.randint(1,10)}/")
    if images:
        nsfw_web_cache[category] = images
        cache_timestamp[category] = time.time()
        return random.choice(images)
    return None

def get_local_nsfw_file(category):
    cat_dir = NSFW_CATEGORIES.get(category, os_module.path.join(NSFW_DIR,"waifu"))
    files = []
    for ext in ["*.jpg","*.jpeg","*.png","*.gif","*.webp"]:
        files.extend(glob.glob(os_module.path.join(cat_dir, ext)))
    if files:
        fp = random.choice(files)
        return discord.File(fp), os_module.path.basename(fp)
    return None, None

# ========== EVENTS ==========
@bot.event
async def on_ready():
    print(f"✅ Bot Online: {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/help"))
    await bot.tree.sync()

# ========== HELP ==========
@bot.tree.command(name="help", description="Menu")
async def help_cmd(interaction):
    embed = create_embed(title="🤖 BOT v5.0", description="**Auto Setup + NSFW + Game + Fun**", color=discord.Color.purple(),
        fields=[
            {"name":"🚀 Setup","value":"`/autosetup` - Tạo server (giữ kênh cũ)","inline":False},
            {"name":"🔞 NSFW","value":"`/nsfw waifu` `/nsfw hentai` `/nsfw boobs` `/nsfw list`","inline":False},
            {"name":"⚔️ Game","value":"`/create` `/profile` `/battle` `/shop` `/daily`","inline":False},
            {"name":"😂 Fun","value":"`/meme` `/dice` `/coin` `/8ball` `/hack` `/ship` `/iq` `/gay`","inline":False},
        ])
    await interaction.response.send_message(embed=embed)

# ========== NSFW (KHÔNG GIỚI HẠN KÊNH) ==========
@bot.tree.command(name="nsfw", description="NSFW 18+")
@app_commands.choices(category=[app_commands.Choice(name=n.title(), value=n) for n in NSFW_CATEGORIES]+[app_commands.Choice(name="Danh sách", value="list")])
async def nsfw_cmd(interaction, category="waifu"):
    if category == "list":
        await interaction.response.send_message(embed=create_embed(title="🔞 NSFW LIST", description=", ".join(NSFW_CATEGORIES.keys()), color=discord.Color.dark_red()))
        return
    await interaction.response.defer()
    url = await get_web_nsfw_url(category)
    if url:
        await interaction.followup.send(embed=create_embed(title=f"🔞 {category.upper()}", color=discord.Color.dark_red(), image=url, footer="NSFW | 18+"))
        return
    file, name = get_local_nsfw_file(category)
    if file:
        await interaction.followup.send(embed=create_embed(title=f"🔞 {category.upper()}", footer=f"Local: {name}", color=discord.Color.dark_red()), file=file)
    else:
        await interaction.followup.send("❌ Không có ảnh!")

# ========== AUTO SETUP (KHÔNG XÓA KÊNH CŨ) ==========
@bot.tree.command(name="autosetup", description="Tạo server (giữ kênh cũ)")
@app_commands.default_permissions(administrator=True)
async def autosetup_cmd(interaction):
    guild = interaction.guild
    await interaction.response.defer(ephemeral=True)
    created = []
    # Roles
    for rc in AUTO_SERVER_CONFIG["roles"]:
        if not discord.utils.get(guild.roles, name=rc["name"]):
            try:
                perms = discord.Permissions()
                for p in rc.get("permissions",[]):
                    try: setattr(perms, p, True)
                    except: pass
                await guild.create_role(name=rc["name"], color=discord.Color(rc["color"]), permissions=perms, hoist=rc.get("hoist",False), mentionable=True)
                created.append(f"✅ Role: {rc['name']}")
            except: pass
    # Categories
    for cc in AUTO_SERVER_CONFIG["categories"]:
        if not discord.utils.get(guild.categories, name=cc["name"]):
            try:
                cat = await guild.create_category(name=cc["name"])
                if "NSFW" in cc["name"].upper():
                    await cat.set_permissions(guild.default_role, view_channel=False)
                created.append(f"✅ Category: {cc['name']}")
            except: pass
    # Channels
    nsfw_role = discord.utils.get(guild.roles, name="🔞 NSFW Access")
    for ch in AUTO_SERVER_CONFIG["channels"]:
        if not (discord.utils.get(guild.text_channels, name=ch["name"]) or discord.utils.get(guild.voice_channels, name=ch["name"])):
            try:
                cat = discord.utils.get(guild.categories, name=ch["category"])
                if ch["type"] == "text":
                    nc = await guild.create_text_channel(name=ch["name"], category=cat, topic=ch.get("topic",""), nsfw=ch.get("nsfw",False))
                else:
                    nc = await guild.create_voice_channel(name=ch["name"], category=cat)
                created.append(f"✅ {ch['type']}: {ch['name']}")
                # Gửi welcome + verify cho kênh xác nhận 18+
                if ch["name"] == "🔞-xác-nhận" and nsfw_role:
                    try: await nc.purge(limit=5)
                    except: pass
                    class V(discord.ui.View):
                        def __init__(self): super().__init__(timeout=None)
                        @discord.ui.button(label="✅ Tôi trên 18 tuổi", style=discord.ButtonStyle.green, custom_id="v18nsfw")
                        async def ok(self, bi, b):
                            r = discord.utils.get(bi.guild.roles, name="🔞 NSFW Access")
                            if r and r not in bi.user.roles:
                                await bi.user.add_roles(r)
                                await bi.response.send_message("✅ Thành công! Vào 🔞-nsfw nhé!", ephemeral=True)
                            else: await bi.response.send_message("✅ Đã xác nhận!", ephemeral=True)
                    await nc.send(embed=create_embed(title="🔞 XÁC NHẬN 18+", description="Nhấn nút để xác nhận bạn trên 18 tuổi.", color=discord.Color.dark_red()), view=V())
                # Gửi hướng dẫn kênh NSFW
                if ch["name"] == "🔞-nsfw":
                    try: await nc.purge(limit=5)
                    except: pass
                    await nc.send(embed=create_embed(title="🔞 KÊNH NSFW", description="Dùng `/nsfw waifu`, `/nsfw hentai`, `/nsfw boobs`, `/nsfw list`...", color=discord.Color.dark_purple()))
                # Gửi welcome kênh chat 18+
                if ch["name"] == "🔞-chat":
                    try: await nc.purge(limit=5)
                    except: pass
                    await nc.send(embed=create_embed(title="💬 CHAT 18+", description="Chào mừng đến phòng chat 18+!", color=discord.Color.gold()))
            except: pass
    # Welcome kênh welcome
    wc = discord.utils.get(guild.text_channels, name="👋-welcome")
    if wc:
        try: await wc.purge(limit=5)
        except: pass
        await wc.send(embed=create_embed(title="👋 CHÀO MỪNG", description="Chào mừng đến server!\nĐọc luật tại 📜-luật\n🔞 Vào 🔞-xác-nhận để verify 18+", color=discord.Color.green()))
    # Luật
    rc = discord.utils.get(guild.text_channels, name="📜-luật")
    if rc:
        try: await rc.purge(limit=5)
        except: pass
        await rc.send(embed=create_embed(title="📜 NỘI QUY", description="1. Tôn trọng\n2. Không spam\n3. NSFW chỉ trong kênh 🔞", color=discord.Color.blue()))
    
    await interaction.followup.send(embed=create_embed(title="✅ AUTO SETUP", description="Đã tạo:\n"+"\n".join(created) if created else "Tất cả đã có!", color=discord.Color.green()), ephemeral=True)

# ========== CLEAR ==========
@bot.tree.command(name="clear", description="Xóa tin nhắn")
@app_commands.default_permissions(manage_messages=True)
async def clear_cmd(interaction, amount: int=10):
    if amount<1: amount=1
    if amount>100: amount=100
    await interaction.response.defer(ephemeral=True)
    try:
        d = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ Xóa {len(d)} tin!", ephemeral=True)
    except: await interaction.followup.send("❌ Thiếu quyền!", ephemeral=True)

# ========== GAME ==========
@bot.tree.command(name="create", description="Tạo nhân vật")
@app_commands.choices(class_name=[app_commands.Choice(name=v["name"], value=k) for k,v in CLASSES.items()])
async def create_cmd(interaction, name: str, class_name: str):
    if interaction.user.id in players: await interaction.response.send_message("❌ Đã có!", ephemeral=True); return
    c = CLASSES[class_name]
    players[interaction.user.id] = {"name":name,"class":class_name,"level":1,"xp":0,"hp":c["hp"],"max_hp":c["hp"],"atk":c["atk"],"def":c["def"],"gold":100,"wins":0,"losses":0}
    await interaction.response.send_message(embed=create_embed(title=f"✅ {c['emoji']} {name}", description=f"❤️{c['hp']} ⚔️{c['atk']} 🛡️{c['def']} 💰100", color=discord.Color.green()))

@bot.tree.command(name="profile", description="Xem nhân vật")
async def profile_cmd(interaction):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ /create!", ephemeral=True); return
    await interaction.response.send_message(f"👤 {p['name']} Lv.{p['level']} | ❤️{p['hp']}/{p['max_hp']} ⚔️{p['atk']} 🛡️{p['def']} 💰{p['gold']} | 🏆{p['wins']}W/{p['losses']}L")

@bot.tree.command(name="battle", description="PvP")
async def battle_cmd(interaction):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ /create!", ephemeral=True); return
    opps = [pp for pid, pp in players.items() if pid != interaction.user.id]
    await interaction.response.defer(); await asyncio.sleep(1)
    if opps:
        opp = random.choice(opps)
        win = p['atk']+random.randint(-5,10) > opp['atk']+random.randint(-5,10)
        if win: p['wins']+=1; opp['losses']+=1; p['gold']+=50; m="🏆 THẮNG"
        else: p['losses']+=1; opp['wins']+=1; m="💀 THUA"
    else:
        win = random.random()<0.5; m = "🏆 THẮNG vs BOT" if win else "💀 THUA vs BOT"
        if win: p['gold']+=30
    await interaction.followup.send(f"⚔️ {m}! 💰 {p['gold']}g")

@bot.tree.command(name="shop", description="Cửa hàng")
async def shop_cmd(interaction):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ /create!", ephemeral=True); return
    items = "\n".join([f"{i['emoji']} **{i['name']}** - {i['price']}💰" for i in ITEMS])
    await interaction.response.send_message(embed=create_embed(title="🛒 SHOP", description=f"💰 {p['gold']}g\n\n{items}\n`/buy <tên>`", color=discord.Color.gold()))

@bot.tree.command(name="buy", description="Mua đồ")
async def buy_cmd(interaction, item_name: str):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ /create!", ephemeral=True); return
    item = next((i for i in ITEMS if i['name'].lower()==item_name.lower()), None)
    if not item: await interaction.response.send_message("❌ Không có!"); return
    if p['gold']<item['price']: await interaction.response.send_message(f"❌ Thiếu {item['price']-p['gold']}g!"); return
    p['gold']-=item['price']; p['inventory'] = p.get('inventory',[]) + [item]
    for k in ['atk','def','hp','spd']:
        if k in item:
            if k=='atk': p['atk']+=item[k]
            elif k=='def': p['def']+=item[k]
            elif k=='hp': p['max_hp']+=item[k]; p['hp']+=item[k]
    await interaction.response.send_message(f"✅ Mua {item['emoji']} **{item['name']}**!")

@bot.tree.command(name="daily", description="Thưởng ngày")
async def daily_cmd(interaction):
    p = check_player(interaction.user.id)
    if not p: await interaction.response.send_message("❌ /create!", ephemeral=True); return
    g = random.randint(50,150); p['gold']+=g
    await interaction.response.send_message(f"🎁 Nhận **{g}** gold!")

# ========== FUN ==========
@bot.tree.command(name="meme", description="Meme")
async def meme_cmd(interaction):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://meme-api.com/gimme", timeout=10) as r:
                if r.status==200:
                    d=await r.json()
                    await interaction.response.send_message(embed=create_embed(title=d.get('title',''), image=d.get('url',''), color=discord.Color.random()))
                    return
    except: pass
    await interaction.response.send_message("😂 Hết meme!")

@bot.tree.command(name="dice", description="Xúc xắc")
async def dice_cmd(interaction): await interaction.response.send_message(f"🎲 **{random.randint(1,6)}**")
@bot.tree.command(name="coin", description="Đồng xu")
async def coin_cmd(interaction): await interaction.response.send_message(f"🪙 **{'Ngửa' if random.random()<0.5 else 'Sấp'}**")
@bot.tree.command(name="8ball", description="Bói")
async def ball_cmd(interaction, question: str):
    await interaction.response.send_message(f"🎱 **{question}**\n➡️ {random.choice(['Chắc chắn','Có vẻ vậy','Không rõ','Hỏi lại','Đừng mong','Không','Triển vọng','Nghi ngờ'])}")
@bot.tree.command(name="hack", description="Hack fake")
async def hack_cmd(interaction, user: discord.User): await interaction.response.send_message(f"💻 Hack {user.name}...\n💀 Done! (jk)")
@bot.tree.command(name="ship", description="Ship")
async def ship_cmd(interaction, u1: discord.User, u2: discord.User):
    r=random.randint(0,100); await interaction.response.send_message(f"💕 {u1.name} x {u2.name}\n❤️ {'█'*(r//10)+'░'*(10-r//10)} **{r}%**")
@bot.tree.command(name="iq", description="IQ")
async def iq_cmd(interaction, user: discord.User=None):
    u=user or interaction.user; await interaction.response.send_message(f"🧠 {u.mention}: **{random.randint(1,200)}**")
@bot.tree.command(name="gay", description="Độ gay")
async def gay_cmd(interaction, user: discord.User=None):
    u=user or interaction.user; p=random.randint(1,100)
    await interaction.response.send_message(f"🏳️‍🌈 {u.mention} gay **{p}%**")

# ========== START ==========
if __name__ == "__main__":
    try: bot.run(BOT_TOKEN)
    except Exception as e: print(f"❌ {e}")
