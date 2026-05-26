import os
import logging
import sys
import asyncio
import random
import string

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
    logger.error("❌ BOT_TOKEN not set!")
    sys.exit(1)

logger.info(f"✅ BOT_TOKEN loaded")

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Password generation settings
class PasswordStates(StatesGroup):
    waiting_for_length = State()
    waiting_for_options = State()

def generate_password(length: int, use_upper: bool, use_lower: bool, use_digits: bool, use_symbols: bool) -> str:
    """Generate a secure random password"""
    chars = ""
    if use_upper:
        chars += string.ascii_uppercase
    if use_lower:
        chars += string.ascii_lowercase
    if use_digits:
        chars += string.digits
    if use_symbols:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    if not chars:
        chars = string.ascii_lowercase  # fallback
    
    password = ''.join(random.choice(chars) for _ in range(length))
    return password

def get_length_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔢 8 chars", callback_data="len_8"),
         InlineKeyboardButton(text="🔢 12 chars", callback_data="len_12")],
        [InlineKeyboardButton(text="🔢 16 chars", callback_data="len_16"),
         InlineKeyboardButton(text="🔢 20 chars", callback_data="len_20")],
        [InlineKeyboardButton(text="🔢 24 chars", callback_data="len_24"),
         InlineKeyboardButton(text="🔢 32 chars", callback_data="len_32")],
        [InlineKeyboardButton(text="✏️ Custom", callback_data="len_custom")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_options_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔤 Uppercase (A-Z)", callback_data="opt_upper")],
        [InlineKeyboardButton(text="🔡 Lowercase (a-z)", callback_data="opt_lower")],
        [InlineKeyboardButton(text="🔢 Digits (0-9)", callback_data="opt_digits")],
        [InlineKeyboardButton(text="✨ Symbols (!@#)", callback_data="opt_symbols")],
        [InlineKeyboardButton(text="✅ Generate Password", callback_data="opt_generate")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    logger.info(f"/start from {message.from_user.id}")
    await message.answer(
        "🔐 *Password Generator Bot*\n\n"
        "Generate strong, secure passwords instantly.\n\n"
        "📌 *How to use:*\n"
        "1. Choose password length\n"
        "2. Select character types\n"
        "3. Get your secure password!\n\n"
        "✨ *Features:*\n"
        "- Length: 8 to 64 characters\n"
        "- Uppercase / Lowercase letters\n"
        "- Numbers (0-9)\n"
        "- Special symbols (!@#$%)\n"
        "- Cryptographically secure random\n\n"
        "Click below to start 👇",
        parse_mode="Markdown",
        reply_markup=get_length_keyboard()
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 *Commands:*\n"
        "/start - Generate a new password\n"
        "/help - Show this help\n\n"
        "🔒 *Security Tips:*\n"
        "- Use 16+ characters for important accounts\n"
        "- Always include numbers and symbols\n"
        "- Never reuse passwords across sites\n"
        "- Use a password manager to store them\n\n"
        "Click /start to generate a password!",
        parse_mode="Markdown"
    )

@dp.callback_query()
async def handle_callbacks(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    
    if data == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Cancelled. Send /start to try again.")
        await callback.answer()
        return
    
    if data.startswith("len_"):
        length_value = data.replace("len_", "")
        if length_value == "custom":
            await state.set_state(PasswordStates.waiting_for_length)
            await callback.message.edit_text(
                "✏️ Send me a number between 8 and 64 for password length.\n\n"
                "Example: `20`",
                parse_mode="Markdown"
            )
        else:
            length = int(length_value)
            await state.update_data(length=length, use_upper=True, use_lower=True, 
                                    use_digits=True, use_symbols=False)
            await state.set_state(PasswordStates.waiting_for_options)
            await callback.message.edit_text(
                f"📏 *Length:* {length} characters\n\n"
                f"🎛️ Select character types to include:",
                parse_mode="Markdown",
                reply_markup=get_options_keyboard()
            )
        await callback.answer()
        return
    
    if data.startswith("opt_"):
        option = data.replace("opt_", "")
        
        user_data = await state.get_data()
        length = user_data.get("length", 16)
        use_upper = user_data.get("use_upper", True)
        use_lower = user_data.get("use_lower", True)
        use_digits = user_data.get("use_digits", True)
        use_symbols = user_data.get("use_symbols", False)
        
        if option == "upper":
            use_upper = not use_upper
        elif option == "lower":
            use_lower = not use_lower
        elif option == "digits":
            use_digits = not use_digits
        elif option == "symbols":
            use_symbols = not use_symbols
        elif option == "generate":
            if not (use_upper or use_lower or use_digits or use_symbols):
                await callback.answer("Select at least one character type!", show_alert=True)
                return
            
            password = generate_password(length, use_upper, use_lower, use_digits, use_symbols)
            
            # Create status indicators
            status = ""
            status += "✅ " if use_upper else "❌ "
            status += "Uppercase  |  "
            status += "✅ " if use_lower else "❌ "
            status += "Lowercase  |  "
            status += "✅ " if use_digits else "❌ "
            status += "Digits  |  "
            status += "✅ " if use_symbols else "❌ "
            status += "Symbols"
            
            await callback.message.edit_text(
                f"🔐 *Your Secure Password*\n\n"
                f"`{password}`\n\n"
                f"📏 Length: {length}\n"
                f"🎛️ {status}\n\n"
                f"💡 Tap the password to copy it.\n"
                f"Send /start to generate another.",
                parse_mode="Markdown"
            )
            await state.clear()
            await callback.answer()
            return
        
        await state.update_data(length=length, use_upper=use_upper, use_lower=use_lower,
                                use_digits=use_digits, use_symbols=use_symbols)
        
        # Show which options are selected
        upper_status = "✅" if use_upper else "⬜"
        lower_status = "✅" if use_lower else "⬜"
        digits_status = "✅" if use_digits else "⬜"
        symbols_status = "✅" if use_symbols else "⬜"
        
        await callback.message.edit_text(
            f"📏 *Length:* {length} characters\n\n"
            f"🎛️ *Selected options:*\n"
            f"{upper_status} Uppercase (A-Z)\n"
            f"{lower_status} Lowercase (a-z)\n"
            f"{digits_status} Digits (0-9)\n"
            f"{symbols_status} Symbols (!@#$%)\n\n"
            f"Click buttons to toggle, then press GENERATE:",
            parse_mode="Markdown",
            reply_markup=get_options_keyboard()
        )
        await callback.answer()
        return

@dp.message(PasswordStates.waiting_for_length)
async def process_custom_length(message: types.Message, state: FSMContext):
    try:
        length = int(message.text.strip())
        if length < 8:
            await message.answer("❌ Minimum length is 8. Try again or send /start to cancel.")
            return
        if length > 64:
            await message.answer("❌ Maximum length is 64. Try again or send /start to cancel.")
            return
        
        await state.update_data(length=length, use_upper=True, use_lower=True, 
                                use_digits=True, use_symbols=False)
        await state.set_state(PasswordStates.waiting_for_options)
        await message.answer(
            f"📏 *Length:* {length} characters\n\n"
            f"🎛️ Select character types to include:",
            parse_mode="Markdown",
            reply_markup=get_options_keyboard()
        )
    except ValueError:
        await message.answer("❌ Please send a valid number (8-64). Send /start to cancel.")

async def main():
    logger.info("=" * 45)
    logger.info("🔐 PASSWORD GENERATOR BOT STARTING")
    me = await bot.get_me()
    logger.info(f"🤖 Bot: @{me.username}")
    logger.info("=" * 45)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
