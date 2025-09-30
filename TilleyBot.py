import discord, os, re, requests, http, json, csv, time, random
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from html import unescape
from openai import OpenAI

bot_token_file = "~/bot_tokens/TilleyBot.token"
ai_token_file = "~/bot_tokens/deepseek.token"

bot = commands.Bot("!", intents=discord.Intents.none())

def get_bot_token():
    with open(os.path.expanduser(bot_token_file), 'r') as f:
        return f.readline().strip()
def get_ai_token():
    with open(os.path.expanduser(ai_token_file), 'r') as f:
        return f.readline().strip()

def deepseek_query(prompt, context):
    client = OpenAI(api_key=get_ai_token(), base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    return response.choices[0].message.content

def get_catgirl_link():
    url = "https://nekos.moe/api/v1/random/image"
    response = requests.get(url, params={'nsfw': False})
    data = response.json()
    image_id = data['images'][0]['id']
    return f"https://nekos.moe/image/{image_id}"

def translator(inp, to):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": to,
            "dt": "t",
            "q": inp
        }
        r = requests.get(url, params=params)
        data = r.json()
        return "".join(chunk[0] for chunk in data[0] if chunk[0])
    except:
        return "Failed"

def romanizer(inp):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "en",
            "dt": ["t", "rm"],
            "q": inp
        }
        r = requests.get(url, params=params)
        data = r.json()

        romanized = ""
        translated = ""

        for chunk in data[0]:
            if chunk[0]:
                translated += chunk[0]
            if len(chunk) > 3 and chunk[3]:
                romanized += chunk[3]

        return f"{romanized} ({translated})"
    except:
        return "Failed"
        
def get_current_time(gmt_offset):
        offset = timedelta(hours=gmt_offset)
        utc_now = datetime.now(timezone.utc)
        time = utc_now + offset
        time = time.strftime("%H:%M (%I:%M %p)")
        return time

@bot.tree.command(name="printas", description="Say something as the bot")
async def printas(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(message)

@bot.tree.command(name="scramble", description="scramble text")
async def scramble(interaction: discord.Interaction, message: str):
    substitutions = [('a', 'а'), ('e', 'е'), ('i', 'і'), ('p', 'р'),
                     ('s', 'ѕ'), ('c', 'с'), ('o', 'о'), ('x', 'х'),
                     ('y', 'у')]
    for old, new in substitutions:
        message = message.replace(old, new)
    message = '​'.join(list(message))
    await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="translate", description="translate messages")
async def translate(interaction: discord.Interaction, message: str, lang: str = "en"):
    await interaction.response.send_message(translator(message, lang), ephemeral=True)

@bot.tree.command(name="romanize", description="romanize messages")
async def romanize(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(romanizer(message), ephemeral=False)
    
@bot.tree.command(name="catgirl", description="send a catgirl")
async def catgirl(interaction: discord.Interaction):
    await interaction.response.send_message(get_catgirl_link(), ephemeral=False)

@bot.tree.command(name="timezones", description="calculate timezones")
async def timezones(interaction: discord.Interaction, gmt_offset: int = None):
    if gmt_offset is not None:
        gmt_offset = timedelta(hours=gmt_offset)
        utc_now = datetime.utcnow()
        their_time = utc_now + gmt_offset
        their_time = their_time.strftime("%I:%M %p")
        await interaction.response.send_message(f"Their time is {their_time}", ephemeral=True)
    else:
        await interaction.response.send_message("http://www.hoelaatishetnuprecies.nl/wp-content/uploads/2015/03/world-timezone-large.jpg")

@bot.tree.command(name="senakot_time", description="print info about senakot's time")
async def senakot_time(interaction):
    await interaction.response.send_message(f"Senakot's current time is {get_current_time(4)}. He lives in UTC+4.")

@bot.tree.command(name="kybe_time", description="print info about 2kybe3's time")
async def kybe_time(interaction):
    await interaction.response.send_message(f"Kybe's current time is {get_current_time(2)}. He lives in UTC+2.")

@bot.tree.command(name="hidetext", description="hide text behind other text")
async def hidetext(interaction: discord.Interaction, showntext: str, hidetext: str):
    spoiler = "||​" * 400
    await interaction.response.send_message(f"```{showntext}  {spoiler} _ _ _ _ _ _  {hidetext}```", ephemeral=True)

@bot.tree.command(name="umamusume", description="send a horse girl")
async def umamusume(interaction: discord.Interaction):
    with open("/home/tilley/umas.txt", 'r') as file:
        lines = file.readlines()
    await interaction.response.send_message(random.choice(lines).strip())

@bot.tree.command(name="umacard", description="send a horse girl card")
async def umacard(interaction: discord.Interaction):
    with open('/home/tilley/cards.txt', 'r') as file:
        cards = file.read().strip().split()
    random_card = random.choice(cards)
    await interaction.response.send_message(f"https://umamusu.wiki/w/thumb.php?f=Support_Card_{random_card}_Card.png&width=360")
    
@bot.tree.command(name="deepseek", description="get response from deepseek")
async def deepseek(interaction: discord.Interaction, prompt: str):
    await interaction.response.send_message(prompt)
    await interaction.followup.send(deepseek_query(prompt, "You are a discord bot called Tilley Bot who answers questions in a discord server. do not include emojis and be relatively serious. Keep all responses under 1950 characters."))

@bot.tree.command(name="status_paid", description="send fake status paid message until noxbotv2 comes out")
async def status_paid(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Status changed!",
        description="Status of your order has changed.",
        color=0xFFFF00
    )
    embed.add_field(name="**Paid**", value="We got your payment. Please be patient and wait for delivery guy to pick you up.", inline=False)
    await interaction.response.send_message(embed=embed)

last_message = None

@bot.tree.command(name="do_the_thing", description="custom response")
async def do_the_thing(interaction: discord.Interaction, message: str = None):
    global last_message
    if message:
        last_message = message
        await interaction.response.send_message(f"next response will be {message}", ephemeral=True)
    elif last_message:
        await interaction.response.send_message(last_message)
    else:
        await interaction.response.send_message("please specify message", ephemeral=True)
    
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"connected to {bot.user}")
    
bot.run(get_bot_token())
