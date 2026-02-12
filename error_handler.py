import traceback


def send_error(bot_name: str, error: Exception, bot, admin_id):
    """Отправляет сообщение об ошибке админу в Telegram."""
    error_text = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    message = f"🚨 *Ошибка в боте {bot_name}:*\n" f"```\n{error_text}\n```"
    bot.send_message(chat_id=admin_id, text=message, parse_mode="Markdown")
