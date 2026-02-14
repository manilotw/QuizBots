import random
import redis
import vk_api as vk

from functools import partial
from environs import Env
from telegram import Bot
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

from error_handler import send_error
from questions_parser import clean_answer, parse_questions_answers


def create_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("Новый вопрос", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Сдаться", color=VkKeyboardColor.NEGATIVE)
    return keyboard


def send_question(vk_api, user_id, qa, redis_client):
    question_text, _ = random.choice(list(qa.items()))
    redis_client.set(user_id, question_text)

    vk_api.messages.send(
        peer_id=user_id,
        message=question_text,
        random_id=get_random_id(),
        keyboard=create_keyboard().get_keyboard(),
    )


def handle_message(event, vk_api, qa, redis_client):
    user_id = f"vk_{event.user_id}"
    text = event.text.lower()

    if text == "начать":
        vk_api.messages.send(
            peer_id=user_id,
            message="Нажми «Новый вопрос»",
            random_id=get_random_id(),
            keyboard=create_keyboard().get_keyboard(),
        )
        return

    if text == "новый вопрос":
        send_question(vk_api, user_id, qa, redis_client)
        return

    if text == "сдаться":
        saved_question = redis_client.get(user_id)

        if saved_question and saved_question in qa:
            vk_api.messages.send(
                peer_id=user_id,
                message=qa[saved_question],
                random_id=get_random_id(),
            )

            send_question(vk_api, user_id, qa, redis_client)
        else:
            vk_api.messages.send(
                peer_id=user_id,
                message="Сначала нажмите «Новый вопрос»",
                random_id=get_random_id(),
            )
        return

    saved_question = redis_client.get(user_id)

    if not saved_question or saved_question not in qa:
        vk_api.messages.send(
            peer_id=user_id,
            message="Сначала нажмите «Новый вопрос»",
            random_id=get_random_id(),
        )
        return

    correct_answer = qa[saved_question]

    if clean_answer(text) == clean_answer(correct_answer):
        vk_api.messages.send(
            peer_id=user_id,
            message="Правильно! Поздравляю!",
            random_id=get_random_id(),
        )
    else:
        vk_api.messages.send(
            peer_id=user_id,
            message="Неправильно... Попробуешь ещё раз?",
            random_id=get_random_id(),
        )


def main():
    env = Env()
    env.read_env()

    questions_answers = parse_questions_answers()

    redis_client = redis.Redis(
        host=env.str("REDIS_URL"),
        port=env.int("REDIS_PORT"),
        password=env.str("REDIS_PASSWORD"),
        decode_responses=True,
    )

    bot = Bot(token=env.str("TELEGRAM_BOT_TOKEN"))
    admin_id = env.str("TELEGRAM_CHAT_ID")

    try:
        vk_session = vk.VkApi(token=env.str("VK_API_KEY"))
        vk_api = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)

        handler = partial(
            handle_message,
            vk_api=vk_api,
            qa=questions_answers,
            redis_client=redis_client,
        )

        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                handler(event)

    except Exception as e:
        send_error("VK Bot", e, bot, admin_id)


if __name__ == "__main__":
    main()
