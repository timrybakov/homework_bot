import os
import sys
import logging
import time

import requests
from http import HTTPStatus
from telegram import Bot

from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
TWO_MONTH = 5259486
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.INFO,
    filename='my_log.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def check_tokens():
    """Проверка доступности токенов в перменных окружения."""
    tokens = {
        PRACTICUM_TOKEN: 'PRACTICUM_TOKEN',
        TELEGRAM_TOKEN: 'TELEGRAM_TOKEN',
        TELEGRAM_CHAT_ID: 'TELEGRAM_CHAT_ID'
    }
    for token in tokens:
        if not token:
            logging.critical(f'Отсутствие обязательной переменной '
                             f'окружения: {tokens[token]}')
            sys.exit()
        else:
            logging.info(f'Переменная окружения '
                         f'{tokens[token]} получена успешно')


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Бот успешно отправил сообщение')
    except Exception:
        logging.error(f'Произошла ошибка при отправке сообщения: {Exception}')


def get_api_answer(timestamp):
    """Запрос к API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except Exception:
        logging.error(f'Сбой в работе программы: '
                      f'Эндпоинт {ENDPOINT} недоступен. '
                      f'Код ответа API: {response.status_code}')
        raise Exception
    status = response.status_code
    if status != HTTPStatus.OK:
        raise Exception(f'Статус ответа {status} != 200')
    return response.json()


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError('response не является словарем')
    if 'homeworks' not in response:
        raise KeyError('В ответе API домашки нет ключа "homeworks"')
    if 'current_date' not in response:
        raise KeyError('В ответе API домашки нет ключа "current_date"')
    if not isinstance(response['current_date'], int):
        raise TypeError('response["current_date"] не число')
    if not isinstance(response['homeworks'], list):
        raise TypeError('response["homeworks"] не список')


def parse_status(homework):
    """Парсинг ответа от API."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('В ответе не обнаружен ключ "homework_name"')
    if 'status' not in homework:
        raise KeyError('В ответе не обнаружен ключ "status"')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(
            f'Статус домашней работы {homework_status}'
            f' не соответствует документации'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - TWO_MONTH
    previous_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response.get('homeworks')
            if homework:
                new_message = parse_status(homework[0])
                if new_message != previous_message:
                    send_message(bot, new_message)
                    previous_message = new_message
            else:
                logging.info('Домашних заданий еще нет')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
