import os
import sys
import logging
import time

import requests
from http import HTTPStatus

import telegram.error
from telegram import Bot

from dotenv import load_dotenv

from exceptions import (
    ConnectionException, TimeOutException, UnusualAPIException
)

BASE_DIR = os.path.abspath(__file__)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности токенов в перменных окружения."""
    tokens = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    global_values = globals()
    list_of_tokens = []
    for token_name in tokens:
        token = global_values.get(token_name)
        if not token:
            logging.critical(f'Отсутствие обязательной переменной '
                             f'окружения: {token_name}')
        else:
            list_of_tokens.append(token_name)
            logging.info(f'Переменная окружения '
                         f'{token_name} получена успешно')

    if len(list_of_tokens) != len(tokens):
        sys.exit(1)


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        logging.info(message)
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Бот успешно отправил сообщение')
    except telegram.error.TelegramError as error:
        logging.error(f'Произошла ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Запрос к API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.ConnectionError as error:
        raise ConnectionException from error
    except requests.Timeout as error:
        raise TimeOutException from error
    except Exception:
        raise UnusualAPIException

    status = response.status_code
    if status != HTTPStatus.OK:
        raise Exception(f'Статус ответа {status} != 200')
    return response.json()


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError(f'response не является словарем {type(response)}')

    if 'homeworks' not in response:
        raise KeyError('В ответе API домашки нет ключа "homeworks"')

    if 'current_date' not in response:
        raise KeyError('В ответе API домашки нет ключа "current_date"')

    if not isinstance(response['current_date'], int):
        answer = response['current_date']
        raise TypeError(f'response["current_date"] не число {answer}')

    if not isinstance(response['homeworks'], list):
        answer = response['homeworks']
        raise TypeError(f'response["homeworks"] не список {answer}')


def parse_status(homework):
    """Парсинг ответа от API."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name"')

    homework_name = homework.get('homework_name')

    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status"')

    homework_status = homework.get('status')

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
    timestamp = int(time.time())
    previous_message = None
    prev_error_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            timestamp = response.get('current_date')
            homework = response.get('homeworks')
            if homework:
                new_message = parse_status(homework[0])
                if new_message != previous_message:
                    send_message(bot, new_message)
                    previous_message = new_message
            else:
                logging.debug('Домашних заданий еще нет')

        except Exception as error:
            new_error_message = f'{error}'
            if prev_error_message != new_error_message:
                logging.error(new_error_message, exc_info=True)
                send_message(bot, new_error_message)
                prev_error_message = new_error_message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename=f'{BASE_DIR}.log',
        format=('%(asctime)s, %(levelname)s, %(lineno)d, '
                '%(funcName)s, %(message)s, %(name)s')
    )
    main()
