import logging
import re
import time
from json.decoder import JSONDecodeError

import requests

from .models import CustomerProfile


def fetch_messages(sms_webhook_token):
    try:
        url = f"https://webhook.site/token/{sms_webhook_token}/requests?page=1&sorting=newest"
        return requests.get(url).json()["data"]
    except JSONDecodeError:
        raise Exception("sms_webhook_token is incorrect")


def clear_message(sms_webhook_token, message_id=""):
    url = f"https://webhook.site/token/{sms_webhook_token}/request/{message_id}"
    requests.delete(url)


def wait_for_code(context: CustomerProfile, max_wait: int = 120):
    polls = max_wait // 5
    for i in range(polls):
        messages = fetch_messages(context.sms_webhook_token)
        if not messages:
            if i % 6 == 0:
                logging.info(f"Waiting for SMS code ({i * 5}s / {max_wait}s)...")
            time.sleep(5)
            continue

        content = messages[0].get("text_content")
        match = re.search("CODIGO (.*), DE", content)
        if match:
            clear_message(context.sms_webhook_token, messages[0].get("uuid"))
            return match.group(1)

    logging.warning(f"SMS code not received within {max_wait}s")
    return None
