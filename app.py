import os
import logging
import sys
import random
import asyncio
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import aiohttp
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

# Get Render URL (required for webhook)
RENDER_URL = os.getenv("RENDER_URL")
if not RENDER_URL:
    logger.warning("⚠️ RENDER_URL not set. Webhook will use localhost")
    RENDER_URL = "https://your-service-name.onrender.com"

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Flask app for health checks
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "✅ Bot is running", 200

# Random number generator functions
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
        "1. Choose a range (1-6, 1-10, 1-20, 1-100)\n"
        "2. Or set a custom range (e.g., 50-200)\n"
        "3. Get your random number!\n\n"
        "✨ *Features:*\n"
        "- Dice rolls (1-6)\n"
        "- Custom ranges\n"
        "- Cryptographically secure\n\n"
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
        "🎲 *Examples:*\n"
        "- Dice roll: 1-6\n"
        "- Custom: 50-200\n"
        "- Coin flip: 1-2\n\n"
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
            "✏️ Send me a custom range in this format:\n\n"
            "`min max`\n\n"
            "Example: `1 100`\n"
            "Example: `50 200`\n\n"
            "Send /start to cancel.",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    if data.startswith("dice_"):
        range_str = data.replace("dice_", "")
        min_val, max_val = map(int, range_str.split("_"))
        random_num = random.randint(min_val, max_val)
        
        # Create visual representation
        if max_val == 6:
            dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
            visual = dice_faces[random_num - 1]
        else:
            visual = "🎲"
        
        await callback.message.edit_text(
            f"{visual} *Your Random Number*\n\n"
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
            await message.answer(
                "❌ Invalid format. Send: `min max`\n\n"
                "Example: `1 100`\n"
                "Send /start to try again.",
                parse_mode="Markdown"
            )
            return
        
        min_val = int(parts[0])
        max_val = int(parts[1])
        
        if min_val >= max_val:
            await message.answer("❌ Minimum must be less than maximum. Send /start to try again.")
            return
        
        if max_val - min_val > 1000000:
            await message.answer("❌ Range too large (max 1,000,000 difference).")
            return
        
        random_num = random.randint(min_val, max_val)
        
        await message.answer(
            f"🎲 *Your Random Number*\n\n"
            f"**{random_num}**\n\n"
            f"🎯 Range: {min_val} to {max_val}\n\n"
            f"Send /start to generate another.",
            parse_mode="Markdown"
        )
    except ValueError:
        await message.answer("❌ Please send numbers only. Example: `1 100`", parse_mode="Markdown")

async def on_startup(bot: Bot):
    """Setup webhook on startup"""
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook set to: {WEBHOOK_URL}")

async def on_shutdown(bot: Bot):
    """Cleanup on shutdown"""
    await bot.delete_webhook()
    logger.info("❌ Webhook deleted")

async def main():
    """Setup aiohttp web server with webhook"""
    aiohttp_app = web.Application()
    
    # Setup webhook handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(aiohttp_app, path=WEBHOOK_PATH)
    
    # Register startup/shutdown events
    aiohttp_app.on_startup.append(lambda _: on_startup(bot))
    aiohttp_app.on_shutdown.append(lambda _: on_shutdown(bot))
    
    # Run Flask health check in background thread
    import threading
    def run_flask():
        port = int(os.environ.get("PORT", 8080))
        flask_app.run(host="0.0.0.0", port=port, use_reloader=False, debug=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info("=" * 45)
    logger.info("🎲 RANDOM NUMBER BOT STARTING (Webhook Mode)")
    logger.info(f"🤖 Bot: {(await bot.get_me()).username}")
    logger.info(f"🔗 Webhook URL: {WEBHOOK_URL}")
    logger.info("=" * 45)
    
    # Run aiohttp server
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
