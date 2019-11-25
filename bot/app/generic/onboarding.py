from aiogram import types
from aiogram.dispatcher import FSMContext
# from aiogram.types import ParseMode
# import aiogram.utils.markdown as md
from aiogram.dispatcher.filters.state import State, StatesGroup

from loguru import logger
# States
from bot.app.core import bot, _, LANG_codes, LANGS
from bot.app.generic import generic
from bot.bot_utils import mysql_connect, bot_utils

LEVELS = {}


class Form(StatesGroup):
    L1 = State()  # Will be represented in storage as 'Form:L1'
    L2 = State()  # Will be represented in storage as 'Form:L2'
    level = State()  # Will be represented in storage as 'Form:level'


async def onboarding_start(user):
    """
    Conversation's entry point
    """
    logger.info("{} started onboarding", user)
    # Set state
    await Form.L1.set()

    await bot.send_message(user, _("Hi there! What is your language?"))


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
    kb_data = [
        (("Know nothing", 0, '_'), ("Know a bit", 10, '_')),
        (("Intermediate", 20, '_'), ("Advanced", 30,'_'))
    ]
    kb = bot_utils.flexy_keyboard(kb_data)

    async with state.proxy() as data:
        lang = data['L2']
    await message.reply(_("OK, you want to learn {}. How do you estimate your language level?")
                        .format(lang), reply_markup=kb)


async def process_level_invalid(message: types.Message):

    return await message.reply(_("Please, choose your language level from the keyboard."))


def get_lang(lang):
    if lang in LANG_codes.keys():
        return LANG_codes[lang]
    elif lang in LANGS:
            return lang
    else:
        return None


async def process_level_query(query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['level'] = str(query.data).split(':')[1]

        # Remove keyboard
        # markup = types.ReplyKeyboardRemove()

        # And send message
        # await bot.send_message(
        #     query.from_user.id,
        #     md.text(
        #         md.text(_('Your language is '), md.bold(data['L1'])),
        #         md.text(_('You want to learn '), md.code(data['L2'])),
        #         md.text(_('Level:'), data['level']),
        #         sep='\n',
        #     ),
        #     reply_markup=markup,
        #     parse_mode=ParseMode.MARKDOWN,
        #
        # )
        l1 = get_lang(data['L1'])
        if l1 is None:
            await bot.send_message(query.from_user.id, "Sorry, {} is not supported. Make sure you "
                                                       "there is no mistake and try again")
            await query.message.delete_reply_markup()
            # Finish conversation
            await state.finish()
            logger.warning("Language is wrong: {} {} {} {} {} {} ", query.from_user.id,
                                  query.from_user.first_name,
                                  query.from_user.last_name,
                                  l1,
                                  data['L2'],
                                  data['level'])
            return

        l2 = get_lang(data['L2'])
        if l2 is None:
            await bot.send_message(query.from_user.id, "Sorry, {} is not supported. Make sure you "
                                                       "there is no mistake and try again")
            await query.message.delete_reply_markup()
            # Finish conversation
            await state.finish()
            logger.warning("Language is wrong: {} {} {} {} {} {} ", query.from_user.id,
                                  query.from_user.first_name,
                                  query.from_user.last_name,
                                  l1,
                                  l2,
                                  data['level'])
            return

        logger.info("adding new user: {} {} {} {} {} {} ", query.from_user.id,
                                  query.from_user.first_name,
                                  query.from_user.last_name,
                                  l1,
                                  l2,
                                  data['level'])
        mysql_connect.update_user(query.from_user.id,
                                  query.from_user.first_name,
                                  query.from_user.last_name,
                                  l1,
                                  l2,
                                  data['level'])
    await query.message.delete_reply_markup()
    # Finish conversation
    await state.finish()
    await generic.start_message(query.from_user.id)
    return