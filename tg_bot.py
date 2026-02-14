#!/usr/bin/env python

import logging
import random
import redis

from functools import partial
from environs import Env
from telegram import Bot, ReplyKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
)

from error_handler import send_error
from questions_parser import clean_answer, parse_questions_answers


WAITING_FOR_ANSWER = 1


def start(update, context):
    keyboard = [["Новый вопрос", "Сдаться"], ["Мой счет"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(
        "Я бот для викторин. Нажми «Новый вопрос».",
        reply_markup=markup,
    )


def handle_new_question_request(update, context, qa, redis_client):
    user_id = f"tg_{update.message.from_user.id}"
    question_text, _ = random.choice(list(qa.items()))

    redis_client.set(user_id, question_text)
    update.message.reply_text(question_text)

    return WAITING_FOR_ANSWER


def handle_solution_attempt(update, context, qa, redis_client):
    user_id = f"tg_{update.message.from_user.id}"
    user_answer = update.message.text

    saved_question = redis_client.get(user_id)

    if not saved_question or saved_question not in qa:
        update.message.reply_text("Сначала нажмите «Новый вопрос».")
        return ConversationHandler.END

    correct_answer = qa[saved_question]

    if clean_answer(user_answer) == clean_answer(correct_answer):
        update.message.reply_text(
            "Правильно! Поздравляю!\nДля следующего вопроса нажми «Новый вопрос»."
        )
        return ConversationHandler.END
    else:
        update.message.reply_text("Неправильно... Попробуешь ещё раз?")
        return WAITING_FOR_ANSWER


def handle_give_up(update, context, qa, redis_client):
    user_id = f"tg_{update.message.from_user.id}"

    saved_question = redis_client.get(user_id)

    if saved_question and saved_question in qa:
        update.message.reply_text(qa[saved_question])

    question_text, _ = random.choice(list(qa.items()))
    redis_client.set(user_id, question_text)

    update.message.reply_text(question_text)

    return WAITING_FOR_ANSWER


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    env = Env()
    env.read_env()

    tg_token = env.str("TELEGRAM_BOT_TOKEN")
    admin_id = env.str("TELEGRAM_CHAT_ID")

    qa = parse_questions_answers()

    redis_client = redis.Redis(
        host=env.str("REDIS_URL"),
        port=env.int("REDIS_PORT"),
        password=env.str("REDIS_PASSWORD"),
        decode_responses=True,
    )

    bot = Bot(token=tg_token)

    try:
        updater = Updater(tg_token)
        dispatcher = updater.dispatcher

        dispatcher.add_handler(CommandHandler("start", start))

        conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(
                    Filters.regex("^Новый вопрос$"),
                    partial(handle_new_question_request,
                            qa=qa,
                            redis_client=redis_client),
                )
            ],
            states={
                WAITING_FOR_ANSWER: [
                    MessageHandler(
                        Filters.regex("^Сдаться$"),
                        partial(handle_give_up,
                                qa=qa,
                                redis_client=redis_client),
                    ),
                    MessageHandler(
                        Filters.text & ~Filters.command,
                        partial(handle_solution_attempt,
                                qa=qa,
                                redis_client=redis_client),
                    ),
                ],
            },
            fallbacks=[],
        )

        dispatcher.add_handler(conv_handler)

        updater.start_polling()
        updater.idle()

    except Exception as e:
        send_error("Telegram Bot", e, bot, admin_id)
        raise


if __name__ == "__main__":
    main()
