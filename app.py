import os
import logging
import sys
import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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
    logger.error("❌ BOT_TOKEN environment variable not set!")
    sys.exit(1)

logger.info("✅ BOT_TOKEN loaded successfully")

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# States for custom range
class RangeState(StatesGroup):
    waiting_for_range = State()

def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🎲 1-6", callback_data="range_1_6"),
         InlineKeyboardButton(text="🎯 1-10", callback_data="range_1_10")],
        [InlineKeyboardButton(text="🎲 1-20", callback_data="range_1_20"),
         InlineKeyboardButton(text="🎲 1-100", callback_data="range_1_100")],
        [InlineKeyboardButton(text="✏️ Custom Range", callback_data="range_custom")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    logger.info(f"/start from user {message.from_user.id}")
    await message.answer(
        "🎲 *Random Number Generator Bot*\n\n"
        "Generate random numbers instantly.\n\n"
        "📌 *How to use:*\n"
        "• Click a preset range below\n"
        "• Or choose 'Custom Range' for your own\n\n"
        "👇 *Select a range:*",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 *Commands:*\n"
        "/start - Generate a random number\n"
        "/help - Show this help\n\n"
        "🎲 *Examples:*\n"
        "• 1-6 for a dice roll\n"
        "• 1-100 for percentage\n"
        "• Custom: send `1 1000`\n\n"
        "Send /start to begin!",
        parse_mode="Markdown"
    )

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    
    if data == "range_custom":
        await callback.message.edit_text(
            "✏️ *Custom Range*\n\n"
            "Send two numbers separated by a space:\n\n"
            "`min max`\n\n"
            "Example: `1 100`\n"
            "Example: `50 200`\n\n"
            "Send /start to cancel.",
            parse_mode="Markdown"
        )
        await state.set_state(RangeState.waiting_for_range)
        await callback.answer()
        return
    
    if data.startswith("range_"):
        range_part = data.replace("range_", "")
        min_val, max_val = map(int, range_part.split("_"))
        random_num = random.randint(min_val, max_val)
        
        # Special visual for dice
        if min_val == 1 and max_val == 6:
            dice = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
            visual = dice[random_num - 1]
        else:
            visual = "🎲"
        
        await callback.message.edit_text(
            f"{visual} *Result*\n\n"
            f"**{random_num}**\n\n"
            f"Range: {min_val} to {max_val}\n\n"
            f"Send /start to roll again!",
            parse_mode="Markdown"
        )
        await callback.answer()

@dp.message(RangeState.waiting_for_range)
async def process_custom_range(message: types.Message, state: FSMContext):
    try:
        parts = message.text.strip().split()
        
        if len(parts) != 2:
            await message.answer(
                "❌ Please send exactly two numbers.\n\n"
                "Example: `1 100`\n\n"
                "Send /start to cancel.",
                parse_mode="Markdown"
            )
            return
        
        min_val = int(parts[0])
        max_val = int(parts[1])
        
        if min_val >= max_val:
            await message.answer(
                "❌ Minimum must be less than maximum.\n\n"
                "Example: `1 100`\n\n"
                "Send /start to cancel.",
                parse_mode="Markdown"
            )
            return
        
        if max_val - min_val > 1000000:
            await message.answer(
                "❌ Range too large (max 1,000,000 difference).\n\n"
                "Send /start to try again.",
                parse_mode="Markdown"
            )
            return
        
        random_num = random.randint(min_val, max_val)
        
        await message.answer(
            f"🎲 *Custom Range Result*\n\n"
            f"**{random_num}**\n\n"
            f"Range: {min_val} to {max_val}\n\n"
            f"Send /start to generate another!",
            parse_mode="Markdown"
        )
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Please send valid numbers.\n\n"
            "Example: `1 100`\n\n"
            "Send /start to cancel.",
            parse_mode="Markdown"
        )

@dp.message()
async def unknown_message(message: types.Message):
    await message.answer(
        "🤔 I didn't understand that.\n\n"
        "Send /start to generate random numbers!",
        parse_mode="Markdown"
    )

async def main():
    logger.info("=" * 45)
    logger.info("🎲 RANDOM NUMBER GENERATOR BOT STARTING")
    me = await bot.get_me()
    logger.info(f"🤖 Bot: @{me.username}")
    logger.info(f"🆔 Bot ID: {me.id}")
    logger.info("=" * 45)
    logger.info("✅ Bot is polling for messages...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
