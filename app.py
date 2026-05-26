import os
import logging
import sys
import random
import asyncio
import threading
from flask import Flask
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Check for BOT_TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not set!")
    sys.exit(1)

# Get Render URL
RENDER_URL = os.getenv("RENDER_URL")
if not RENDER_URL:
    logger.warning("⚠️ RENDER_URL not set")
    RENDER_URL = "https://your-service.onrender.com"

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

# Initialize
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "✅ Bot is running", 200

def get_dice_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🎲 1-6", callback_data="dice_1_6"),
         InlineKeyboardButton(text="🎯 1-10", callback_data="dice_1_10")],
        [InlineKeyboardButton(text="🎲 1-20", callback_data="dice_1_20"),
         InlineKeyboardButton(text="🎲 1-100", callback_data="dice_1_100")],
        [InlineKeyboardButton(text="✏️ Custom Range", callback_data="dice_custom")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    logger.info(f"/start from {message.from_user.id}")
    await message.answer(
        "🎲 *Random Number Generator Bot*\n\n"
        "Generate random numbers instantly.\n\n"
        "📌 *How to use:*\n"
        "1. Choose a range\n"
        "2. Get your random number!\n\n"
        "Click below to start 👇",
        parse_mode="Markdown",
        reply_markup=get_dice_keyboard()
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 *Commands:*\n"
        "/start - Generate a random number\n"
        "/help - Show this help\n\n"
        "Send /start to begin!",
        parse_mode="Markdown"
    )

@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    data = callback.data
    
    if data == "cancel":
        await callback.message.edit_text("❌ Cancelled. Send /start to try again.")
        await callback.answer()
        return
    
    if data == "dice_custom":
        await callback.message.edit_text(
            "✏️ Send me a custom range:\n\n"
            "`min max`\n\n"
            "Example: `1 100`\n"
            "Example: `50 200`",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    if data.startswith("dice_"):
        range_str = data.replace("dice_", "")
        min_val, max_val = map(int, range_str.split("_"))
        random_num = random.randint(min_val, max_val)
        
        await callback.message.edit_text(
            f"🎲 *Your Random Number*\n\n"
            f"**{random_num}**\n\n"
            f"🎯 Range: {min_val} to {max_val}\n\n"
            f"Send /start to generate another.",
            parse_mode="Markdown"
        )
        await callback.answer()

@dp.message()
async def handle_custom_range(message: types.Message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.answer("❌ Send: `min max` (e.g., `1 100`)", parse_mode="Markdown")
            return
        
        min_val = int(parts[0])
        max_val = int(parts[1])
        
        if min_val >= max_val:
            await message.answer("❌ Minimum must be less than maximum.")
            return
        
        random_num = random.randint(min_val, max_val)
        
        await message.answer(
            f"🎲 *Your Random Number*\n\n"
            f"**{random_num}**\n\n"
            f"🎯 Range: {min_val} to {max_val}",
            parse_mode="Markdown"
        )
    except ValueError:
        await message.answer("❌ Send numbers only. Example: `1 100`", parse_mode="Markdown")

async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook set to: {WEBHOOK_URL}")

async def main():
    # Setup aiohttp app
    aiohttp_app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(aiohttp_app, path=WEBHOOK_PATH)
    
    # Run Flask in background thread
    def run_flask():
        port = int(os.environ.get("PORT", 8080))
        flask_app.run(host="0.0.0.0", port=port, use_reloader=False)
    
    threading.Thread(target=run_flask, daemon=True).start()
    
    await on_startup()
    
    logger.info("=" * 45)
    logger.info("🎲 RANDOM NUMBER BOT STARTING")
    logger.info(f"🤖 Bot: {(await bot.get_me()).username}")
    logger.info("=" * 45)
    
    # Run aiohttp server
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
