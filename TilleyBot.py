import discord, asyncio, random, os, re, requests, base64
from datetime import datetime
from discord.ext import commands
from selfbot import send_message, send_file, channel_name_from_id
from Crypto.Util.Padding import pad, unpad
from hashlib import sha256
from Crypto.Cipher import AES

bot = commands.Bot("prefix", intents=discord.Intents.none())

# Authorized username and message
AUTHORIZED_USERNAME = "tillay8"
AUTHORIZED_MESSAGE = "You are not authorized to use this command."

with open(os.path.expanduser("~/bot_tokens/TilleyBot_token"), 'r') as f:
    token = f.readline().strip()

def get_passwd():
    with open(os.path.expanduser("./key"), 'r') as f:
        return f.readline().strip()

def get_user_data(user_id):
    headers = {"Authorization": f"Bot {token}"}
    response = requests.get(f"https://discord.com/api/v10/users/{user_id}", headers=headers)
    if response.status_code != 200:
        raise Exception(f"User with that id does not exist")
    return response.json()

def get_user_profile_picture(user_id):
    user_data = get_user_data(user_id)
    if user_data.get("avatar"):
        if user_data["avatar"].startswith("a_"):
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{user_data['avatar']}.gif?size={512}"
        else:
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{user_data['avatar']}.png?size={512}"
    else:
        default_avatar_index = int(user_data.get("discriminator", 0)) % 5
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_avatar_index}.png"
    return avatar_url

def tcrypt(plaintext, passphrase):
    key, iv = sha256((passphrase).encode()).digest(), os.urandom(AES.block_size)
    return base64.b64encode(iv + AES.new(key, AES.MODE_CBC, iv).encrypt(pad(plaintext.encode(), AES.block_size))).decode()

def tdcrypt(ciphertext, passphrase):
    try:
        decoded = base64.b64decode(ciphertext)
        return unpad(AES.new(sha256((passphrase).encode()).digest(), AES.MODE_CBC, decoded[:AES.block_size]).decrypt(decoded[AES.block_size:]), AES.block_size).decode()
    except (ValueError, KeyError): return None

repeat_tasks = {}

def generate_task_id():
    return random.randint(1000, 9999)

@bot.tree.command(name="echo", description="Send a message as tillay8")
async def echo(interaction: discord.Interaction, tosay: str, channel_id: str = None):
    if interaction.user.name != AUTHORIZED_USERNAME:
        await interaction.response.send_message(AUTHORIZED_MESSAGE, ephemeral=True)
        return
    # Use the current channel if no channel_id is provided
    channel_id = interaction.channel.id if not channel_id else int(channel_id)
    await interaction.response.send_message("Echoing", ephemeral=True)
    send_message(channel_id, tosay)

@bot.tree.command(name="test", description="Is bot alive?")
async def test(interaction: discord.Interaction):
    if interaction.user.name != AUTHORIZED_USERNAME:
        await interaction.response.send_message(AUTHORIZED_MESSAGE, ephemeral=True)
        return
    await interaction.response.send_message(interaction.channel, ephemeral=True)

@bot.tree.command(name="maze", description="Generate maze")
async def maze(interaction: discord.Interaction, size: int, channel_id: str = None):
    if interaction.user.name != AUTHORIZED_USERNAME:
        await interaction.response.send_message(AUTHORIZED_MESSAGE, ephemeral=True)
        return
    # Use the current channel if no channel_id is provided
    channel_id = interaction.channel.id if not channel_id else int(channel_id)
    await interaction.response.send_message("Generating maze", ephemeral=True)
    send_message(channel_id, f"-maze {size}")
    await asyncio.to_thread(os.system, f"./maze {size} maze.png")
    send_file(channel_id, "./maze.png")

@bot.tree.command(name="repeat", description="Repeat a message in a channel at a specified interval")
async def repeat(interaction: discord.Interaction, interval: float, message: str, channel: str = None):
    if interaction.user.name != AUTHORIZED_USERNAME:
        await interaction.response.send_message(AUTHORIZED_MESSAGE, ephemeral=True)
        return
    try:
        channel_id = interaction.channel.id  # Use the current channel if no channel_id is provided
        task_id = generate_task_id()
        while task_id in repeat_tasks:
            task_id = generate_task_id()

        up_pattern = re.compile(r"<up(\d+)>")
        down_pattern = re.compile(r"<down(\d+)>")
        second_pattern = re.compile(r"<second>")

        up_match = up_pattern.search(message)
        down_match = down_pattern.search(message)
        second_match = second_pattern.search(message)

        up_counter = int(up_match.group(1)) if up_match else None
        down_counter = int(down_match.group(1)) if down_match else None
        second_counter = 1 if second_match else None

        async def repeat_task():
            nonlocal up_counter, down_counter, second_counter
            while True:
                updated_message = message
                if up_match:
                    updated_message = up_pattern.sub(str(up_counter), updated_message)
                    up_counter += 1
                if down_match:
                    updated_message = down_pattern.sub(str(down_counter), updated_message)
                    down_counter -= 1
                    if down_counter < 0:
                        del repeat_tasks[task_id]
                        break
                if second_match:
                    updated_message = second_pattern.sub(str(second_counter), updated_message)
                    second_counter += interval
                    if str(second_counter).endswith(".0"):
                        second_counter = int(second_counter)

                send_message(channel_id, updated_message)
                await asyncio.sleep(interval)

        task = asyncio.create_task(repeat_task())
        repeat_tasks[task_id] = (task, channel_id)

        await interaction.response.send_message(f"Started repeat: {task_id}", ephemeral=True)
        await interaction.followup.send(f"Channel: {interaction.channel.name}", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"Failed to start repeating task: {e}", ephemeral=True)

@bot.tree.command(name="stop-repeat", description="Stop a repeating task by its ID")
async def stop_repeat(interaction: discord.Interaction, id: int):
    if interaction.user.name != AUTHORIZED_USERNAME:
        await interaction.response.send_message(AUTHORIZED_MESSAGE, ephemeral=True)
        return
    try:
        if id in repeat_tasks:
            task, channel_id = repeat_tasks[id]
            task.cancel()
            del repeat_tasks[id]

            await interaction.response.send_message(f"Stopped repeating task with ID: {id}", ephemeral=True)
            await interaction.followup.send(f"Channel: {interaction.channel.name}", ephemeral=True)
        else:
            await interaction.response.send_message(f"No repeating task found with ID: {id}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to stop repeating task: {e}", ephemeral=True)

@bot.tree.command(name="daily-maze", description="Send a daily maze at a specific time")
async def daily_maze(interaction: discord.Interaction, size: int, hour: int, minute: int, startnum: int):
    if interaction.user.name != AUTHORIZED_USERNAME:
        await interaction.response.send_message(AUTHORIZED_MESSAGE, ephemeral=True)
        return
    try:
        channel_id = interaction.channel.id
        task_id = generate_task_id()
        while task_id in repeat_tasks:
            task_id = generate_task_id()

        async def repeat_task():
            i = startnum
            while True:
                now = datetime.now()
                if now.hour == hour and now.minute == minute:
                    await asyncio.to_thread(os.system, f"./maze {size} maze.png")
                    send_message(channel_id, f"daily maze #{i}")
                    send_file(channel_id, "./maze.png")
                    i += 1
                await asyncio.sleep(60)

        task = asyncio.create_task(repeat_task())
        repeat_tasks[task_id] = (task, channel_id)
        await interaction.response.send_message(f"Started daily maze: {task_id}", ephemeral=True)
        await interaction.followup.send(f"Channel: {interaction.channel.name}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to start daily maze: {e}", ephemeral=True)

@bot.tree.command(name="sendpfp", description="Send pfp of a user")
async def sendpfp(interaction: discord.Interaction, user_id: str):
    if interaction.user.name != AUTHORIZED_USERNAME:
        await interaction.response.send_message(AUTHORIZED_MESSAGE, ephemeral=True)
        return
    await interaction.response.send_message(f"Sending {user_id} pfp", ephemeral=True)
    send_message(interaction.channel.id, get_user_profile_picture(user_id))

@bot.tree.command(name="botprint", description="Say something as the bot")
async def botprint(interaction: discord.Interaction, message: str):
    if interaction.user.name != AUTHORIZED_USERNAME:
        await interaction.response.send_message(AUTHORIZED_MESSAGE, ephemeral=True)
        return
    await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="encrypt", description="encrypt a message using server password")
async def encrypt(interaction: discord.Interaction, message: str):
    if interaction.user.name != AUTHORIZED_USERNAME:
        await interaction.response.send_message(AUTHORIZED_MESSAGE, ephemeral=True)
        return
    await interaction.response.send_message(f"&&{tcrypt(message, get_passwd())}", ephemeral=True)

@bot.tree.command(name="decrypt", description="decrypt a message using server password")
async def decrypt(interaction: discord.Interaction, encrypted: str):
    if interaction.user.name != AUTHORIZED_USERNAME:
        await interaction.response.send_message(AUTHORIZED_MESSAGE, ephemeral=True)
        return
    await interaction.response.send_message(tdcrypt(encrypted[2:], get_passwd()), ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Ready!")

bot.run(token)
