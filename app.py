import os
import logging
import sys
import asyncio
import random
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

logger.info("✅ BOT_TOKEN loaded")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Flask app for health checks
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "✅ Bot is running", 200

def get_dice_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🎲 1-6", callback_data="1_6"),
         InlineKeyboardButton(text="🎯 1-10", callback_data="1_10")],
        [InlineKeyboardButton(text="🎲 1-20", callback_data="1_20"),
         InlineKeyboardButton(text="🎲 1-100", callback_data="1_100")],
        [InlineKeyboardButton(text="✏️ Custom Range", callback_data="custom")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    logger.info(f"✅ /start from user {message.from_user.id}")
    await message.answer(
        "🎲 *Random Number Generator Bot*\n\n"
        "Generate random numbers instantly.\n\n"
        "📌 *How to use:*\n"
        "1. Choose a range below\n"
        "2. Get your random number!\n\n"
        "👇 Click to start:",
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
        "- Click 1-6 for dice roll\n"
        "- Click Custom and send `1 100`",
        parse_mode="Markdown"
    )

@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    data = callback.data
    
    if data == "cancel":
        await callback.message.edit_text("❌ Cancelled. Send /start to try again.")
        await callback.answer()
        return
    
    if data == "custom":
        await callback.message.edit_text(
            "✏️ Send me a custom range:\n\n"
            "`min max`\n\n"
            "Example: `1 100`\n"
            "Example: `50 200`\n\n"
            "Send /start to cancel.",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    # Handle dice rolls (format: "1_6", "1_10", etc.)
    if "_" in data:
        min_val, max_val = map(int, data.split("_"))
        random_num = random.randint(min_val, max_val)
        
        # Dice face for 1-6
        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        visual = dice_faces[random_num - 1] if max_val == 6 else "🎲"
        
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
                "❌ Send two numbers: `min max`\n\nExample: `1 100`",
                parse_mode="Markdown"
            )
            return
        
        min_val = int(parts[0])
        max_val = int(parts[1])
        
        if min_val >= max_val:
            await message.answer("❌ Minimum must be less than maximum.")
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

def run_flask():
    """Run Flask in a separate thread"""
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)

async def run_bot():
    """Run the bot with polling"""
    logger.info("=" * 45)
    logger.info("🎲 RANDOM NUMBER BOT STARTING")
    me = await bot.get_me()
    logger.info(f"🤖 Bot: @{me.username}")
    logger.info("📡 Using polling mode (not webhook)")
    logger.info("=" * 45)
    
    # Start polling (this runs forever)
    await dp.start_polling(bot)

def main():
    """Main function to run both Flask and bot"""
    # Start Flask in background thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask health check server started on port " + os.environ.get("PORT", "8080"))
    
    # Run bot in main thread
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
