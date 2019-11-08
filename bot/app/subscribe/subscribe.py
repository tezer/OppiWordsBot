from loguru import logger
from aiogram import types
from bot.app.core import bot
from bot.bot_utils import mysql_connect as bd
from settings import PAYMENTS_PROVIDER_TOKEN, prices


def get_price(months):
    price = prices[months]
    p = [types.LabeledPrice(label=price['label'], amount=price['amount'])]
    return p


async def subscribe_command(message: types.Message):
    #TODO Check if the user already has subscription
    #TODO If the user has subscription notify them and use this date to calculate the and date
    await bot.send_message(message.chat.id,
                           "*This is a test subscription*"
                           "\nReal cards won't work here, *no money will be debited from your account*."
                           "\nUse this test card number to pay for your subscription:"
                           " `4242 4242 4242 4242`, use any address and "
                           "card date (_any date later than today_), as well as any 3-digit security code"
                           "\n\nThis is your demo invoice:", parse_mode='Markdown')

    await bot.send_message(message.chat.id, 'Some features of our bot are based on paid services, it means that we have '
                                            'to charge for the access to them.'
                                            '\nThe features include:'
                                       '\n*Google voice recognition* for practicing your pronunciation, '
                                       '\n*Google translate* for more accurate translation of the phrases and sentence ' \
                                       'that you want to learn and '
                                       '\n*Google text-to-speech* to master perfect ' \
                                       'pronunciation of your words and phrases.', parse_mode='Markdown')

    await bot.send_invoice(message.chat.id, title='One month subscription',
                           description='Use of paid premium features for one month. In case of any problems, '
                                       'send an email to info@oppi.ai with the description of your problem',
                           provider_token=PAYMENTS_PROVIDER_TOKEN,
                           currency='eur',
                           prices=get_price(1),
                           start_parameter='one-month-subscription',
                           payload='1')


async def checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                        error_message="Sorry, something went wrong. "
                                                      "Please try to pay again a bit later.")


async def got_payment(message: types.Message):
    await bot.send_message(message.chat.id,
                           'Thank you for your payment! Now you can use your premium features.',
                           parse_mode='Markdown')

    bd.set_premium(message.from_user.id, message.successful_payment.invoice_payload)
