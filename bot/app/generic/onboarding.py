from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode
import aiogram.utils.markdown as md
from aiogram.dispatcher.filters.state import State, StatesGroup

from loguru import logger
# States
from bot.app.core import bot, _, LANG_codes
from bot.bot_utils import mysql_connect, bot_utils


class Form(StatesGroup):
    L1 = State()  # Will be represented in storage as 'Form:L1'
    L2 = State()  # Will be represented in storage as 'Form:L2'
    level = State()  # Will be represented in storage as 'Form:level'


async def onboarding_start(message: types.Message):
    """
    Conversation's entry point
    """
    logger.info("{} started onboarding", message.from_user.id)
    # Set state
    await Form.L1.set()

    await message.reply(_("Hi there! What is your language?"))


async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logger.info('Cancelling state {}', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Cancelled.', reply_markup=types.ReplyKeyboardRemove())


async def process_language_invalid(message: types.Message):
    """
    Language is invalid
    """
    return await message.reply(_("Sorry, this language is not supported. Make sure you spelled it correctly."
                               "\nTry again"))

async def process_L1(message: types.Message, state: FSMContext):
    """
    Process user language
    """
    async with state.proxy() as data:
        data['L1'] = message.text

    await Form.next()
    await message.reply(_("What language do you want to study?"))


async def process_L2(message: types.Message, state: FSMContext):
    # Update state and data
    await Form.next()
    await state.update_data(L2=message.text.lower())

    # Configure ReplyKeyboardMarkup
    # bot_utils.to_vertical_keyboard()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(_("Know nothing"), _("Know a bit"))
    markup.add(_("Intermediate"), _("Advanced"))


    async with state.proxy() as data:
        lang = data['L2']
    await message.reply(_("OK, you want to learn {}. How do you estimate your language level?")
                        .format(lang), reply_markup=markup)


async def process_level_invalid(message: types.Message):

    return await message.reply(_("Please, choose your language level from the keyboard."))


async def process_level(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['level'] = message.text

        # Remove keyboard
        markup = types.ReplyKeyboardRemove()

        # And send message
        await bot.send_message(
            message.chat.id,
            md.text(
                md.text(_('Your language is '), md.bold(data['L1'])),
                md.text(_('You want to learn '), md.code(data['L2'])),
                md.text(_('Level:'), data['level']),
                sep='\n',
            ),
            reply_markup=markup,
            parse_mode=ParseMode.MARKDOWN,

        )
        logger.info('user language is "{}", user learns "{}"',
                    LANG_codes[data['L1']], LANG_codes[data['L2']])
        mysql_connect.update_user(message.from_user.id,
                                  message.from_user.first_name,
                                  message.from_user.last_name,
                                  LANG_codes[data['L1']],
                                  LANG_codes[data['L2'],
                                  level)

    # Finish conversation
    await state.finish()