import asyncio
import json
import os
import threading
import socket
import shutil
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import InputReportReasonFake
import random
import re
import socks
from telethon import TelegramClient, events, sync
import concurrent.futures


# Глобальный список прокси
proxy_list = []
proxy_index = 0
proxy_lock = threading.Lock()
total_message_taken = 0


def thread_worker(phone_number):
    asyncio.run(connect_account(phone_number))


def spin(text):
    pattern = re.compile(r'\{([^{}]+)\}')
    while True:
        match = pattern.search(text)
        if not match:
            break
        options = match.group(1).split('|')
        chosen = random.choice(options)
        text = text[:match.start()] + chosen + text[match.end():]
    return text


def load_proxies():
    global proxy_list
    with open('proxy.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line:
                parts = line.split(':')
                if len(parts) == 4:
                    ip, port, username, password = parts
                    proxy = {
                        'proxy_type': 'socks5',
                        'addr': ip,
                        'port': int(port),
                        'username': username,
                        'password': password
                    }
                    proxy_list.append(proxy)
                else:
                    print(f'Неверный формат прокси: {line}')


def get_working_proxy():
    global proxy_index
    while proxy_index < len(proxy_list):
        proxy = proxy_list[proxy_index]
        proxy_index += 1
        if test_proxy(proxy):
            return proxy
    print('Все прокси неработоспособны.')
    exit(1)


def test_proxy(proxy):
    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect((proxy['addr'], proxy['port']))
        s.close()
        return True
    except Exception as e:
        print(f'Прокси {proxy["addr"]}:{proxy["port"]} не работает: {e}')
        return False


def get_account_numbers():
    account_numbers = []
    active_dir = './sessionActive'
    for filename in os.listdir(active_dir):
        if filename.endswith('.json'):
            phone_number = filename.replace('.json', '')
            account_numbers.append(phone_number)
    return account_numbers


async def start_bot(client, bot_username):
    try:
        # Отправляем команду /start боту
        await client.send_message(bot_username, '/start')
        print(f'Команда /start отправлена боту @{bot_username}')
    except Exception as e:
        print(f'Ошибка при отправке команды /start боту @{bot_username}: {e}')


async def take_report(client, bot_entity):
    global total_message_taken
    spintax_text = "{Здравствуйте|Привет|Добрый день|Добрый вечер}, {этот бот занимается фишингом|этот бот осуществляет фишинг|этот бот проводит фишинговые атаки|этот бот занимается мошенничеством|этот бот обманывает пользователей|этот бот ворует данные|этот бот пытается получить личную информацию}, {я потерял свой аккаунт здесь|я потерял здесь свой аккаунт|мой аккаунт был украден|я лишился своего аккаунта из-за него|мой аккаунт был взломан через этого бота|я стал жертвой фишинга из-за этого бота|я потерял доступ к своему аккаунту здесь}."
    result = spin(spintax_text)
    await client(ReportPeerRequest(
        peer=bot_entity,
        reason=InputReportReasonFake(),
        message=result
    ))
    total_message_taken += 1


async def connect_account(phone_number):
    active_dir = './sessionActive'
    used_dir = './sessionUsed'
    death_dir = './sessionDeath'
    os.makedirs(used_dir, exist_ok=True)
    os.makedirs(death_dir, exist_ok=True)

    session_file = os.path.join(active_dir, f'{phone_number}.session')
    json_file = os.path.join(active_dir, f'{phone_number}.json')

    if not os.path.exists(session_file):
        print(f'Сессия для {phone_number} не найдена.')
        shutil.move(json_file, os.path.join(death_dir, f'{phone_number}.json'))
        return
    if not os.path.exists(json_file):
        print(f'JSON файл для {phone_number} не найден.')
        shutil.move(session_file, os.path.join(death_dir, f'{phone_number}.session'))
        return

    with open(json_file, 'r') as f:
        account_params = json.load(f)

    api_id = account_params.get('app_id')
    api_hash = account_params.get('app_hash')

    if not api_id or not api_hash:
        print(f'APP ID или APP Hash не найдены для {phone_number}.')
        shutil.move(session_file, os.path.join(death_dir, f'{phone_number}.session'))
        shutil.move(json_file, os.path.join(death_dir, f'{phone_number}.json'))
        return

    # Получаем рабочий прокси
    with proxy_lock:
        proxy_settings = get_working_proxy()

    client = TelegramClient(
        session_file,
        api_id,
        api_hash,
        proxy=proxy_settings,
        device_model=account_params.get('device', 'PC'),
        system_version=account_params.get('sdk', 'Windows 10'),
        app_version=account_params.get('app_version', '1.0'),
        lang_code=account_params.get('lang_code', 'ru'),
        system_lang_code=account_params.get('system_lang_code', 'ru-RU'),
    )

    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f'Аккаунт {phone_number} не авторизован.')
            shutil.move(session_file, os.path.join(death_dir, f'{phone_number}.session'))
            shutil.move(json_file, os.path.join(death_dir, f'{phone_number}.json'))
            return
        else:
            print(f'Успешное подключение: {phone_number}')
            # Здесь можно добавить дополнительные действия с аккаунтом

            bot_username = 'Prenugarobot'

            try:
                bot_entity = await client.get_entity(bot_username)
            except Exception as e:
                print(f"Не удалось получить сущность бота: {e}")
                exit(1)

            await start_bot(client, bot_username)
            time_to_wait = random.randint(5, 10)
            print(time_to_wait)
            await asyncio.sleep(time_to_wait)
            await take_report(client, bot_entity)

            # После успешного использования перемещаем файлы в used_dir
            client.disconnect()
            await asyncio.sleep(1)
            shutil.move(session_file, os.path.join(used_dir, f'{phone_number}.session'))
            shutil.move(json_file, os.path.join(used_dir, f'{phone_number}.json'))
    except Exception as e:
        print(f'Неизвестная ошибка с {phone_number}: {e}')
        client.disconnect()
        await asyncio.sleep(1)
        # Перемещаем файлы в death_dir
        shutil.move(session_file, os.path.join(death_dir, f'{phone_number}.session'))
        shutil.move(json_file, os.path.join(death_dir, f'{phone_number}.json'))


def main():
    # Загрузка прокси и номеров
    load_proxies()
    account_numbers = get_account_numbers()
    used_numbers = set()

    # Устанавливаем максимальное количество потоков
    max_threads = 30

    # Используем ThreadPoolExecutor для управления потоками
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []
        for phone_number in account_numbers:
            if phone_number in used_numbers:
                continue
            used_numbers.add(phone_number)
            print(phone_number)
            # Добавляем задачу в пул потоков
            futures.append(executor.submit(thread_worker, phone_number))

        # Получаем результаты по мере завершения задач
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # Обрабатываем результат выполнения задачи
            except Exception as e:
                print(f"Задача завершилась с ошибкой: {e}")

    # Ваш код для обработки по завершению
    print(total_message_taken)


if __name__ == '__main__':
    main()
