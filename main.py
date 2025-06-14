import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
REPORT_CHANNEL_ID = int(os.getenv("REPORT_CHANNEL_ID"))
RPC_API = os.getenv("RPC_API")

# Node IDs to monitor
NODE_IDS = [
    "NodeID-BiucSKLqSh6nEFMngUG7iuJM1575apSsG",
    "NodeID-HBpmWphmWNKRwoebovUSC2zmdonooiu7g"
]

API_URL = RPC_API

# Initialize bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

async def fetch_validator_status(node_ids):
    payload = {
        "jsonrpc": "2.0",
        "method": "platform.getCurrentValidators",
        "params": {
            "nodeIDs": node_ids
        },
        "id": 1
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=payload) as resp:
            if resp.status != 200:
                raise Exception(f"API request failed with status {resp.status}")
            data = await resp.json()
            return data["result"]["validators"]

@tasks.loop(minutes=5)
async def check_nodes_periodically():
    try:
        channel = bot.get_channel(REPORT_CHANNEL_ID)
        if channel is None:
            print(f"Channel with ID {REPORT_CHANNEL_ID} not found.")
            return

        validators = await fetch_validator_status(NODE_IDS)
        current_time = int(time.time())
        not_connected = []

        for validator in validators:
            node_id = validator["nodeID"]
            connected = validator["connected"]
            uptime = validator["uptime"]
            start_time = int(validator["startTime"])
            end_time = int(validator["endTime"])

            in_validation_period = start_time <= current_time <= end_time

            if not connected and in_validation_period:
                not_connected.append({
                    "nodeID": node_id,
                    "uptime": uptime
                })

        if not not_connected:
            await channel.send("✅ All nodes active.")
        else:
            count = len(not_connected)
            message_lines = [f"⚠️ {count} node(s) not connected:"]
            for node in not_connected:
                message_lines.append(f"```\n{node['nodeID']}\n```")
                message_lines.append(f"uptime: {node['uptime']}")
            await channel.send("\n".join(message_lines))

    except Exception as e:
        print(f"Error during node check: {e}")

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    check_nodes_periodically.start()

bot.run(TOKEN)