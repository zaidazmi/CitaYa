import logging
import time

import requests

from .models import CustomerProfile
from .notify import notify

CAPSOLVER_API_URL = "https://api.capsolver.com"


class CapSolverError(Exception):
    pass


def capsolver_create_task(api_key: str, task: dict) -> dict:
    resp = requests.post(
        f"{CAPSOLVER_API_URL}/createTask",
        json={"clientKey": api_key, "task": task},
        timeout=30,
    )
    data = resp.json()
    if data.get("errorId", 0) != 0:
        raise CapSolverError(f"{data.get('errorCode')}: {data.get('errorDescription')}")
    return data


def capsolver_get_result(api_key: str, task_id: str, max_wait: int = 120) -> dict:
    for _ in range(max_wait // 3):
        resp = requests.post(
            f"{CAPSOLVER_API_URL}/getTaskResult",
            json={"clientKey": api_key, "taskId": task_id},
            timeout=30,
        )
        data = resp.json()
        if data.get("errorId", 0) != 0:
            raise CapSolverError(f"{data.get('errorCode')}: {data.get('errorDescription')}")
        if data.get("status") == "ready":
            return data["solution"]
        time.sleep(3)
    raise CapSolverError("Timed out waiting for captcha solution")


def capsolver_solve_recaptcha_v3(api_key: str, website_url: str, website_key: str, page_action: str = "") -> str:
    task = {
        "type": "ReCaptchaV3TaskProxyLess",
        "websiteURL": website_url,
        "websiteKey": website_key,
    }
    if page_action:
        task["pageAction"] = page_action

    data = capsolver_create_task(api_key, task)
    if data.get("status") == "ready":
        return data["solution"]["gRecaptchaResponse"]

    solution = capsolver_get_result(api_key, data["taskId"])
    return solution["gRecaptchaResponse"]


def capsolver_solve_image(api_key: str, image_base64: str) -> str:
    task = {
        "type": "ImageToTextTask",
        "body": image_base64,
    }
    data = capsolver_create_task(api_key, task)
    if data.get("status") == "ready":
        return data["solution"]["text"]

    solution = capsolver_get_result(api_key, data["taskId"])
    return solution["text"]


def solve_captcha(page, context: CustomerProfile):
    if context.auto_captcha:
        if not context.capsolver_api_key:
            logging.error("CapSolver API key is empty")
            return None

        if page.query_selector("#reCAPTCHA_site_key"):
            return _solve_recaptcha(page, context)
        elif page.query_selector("img.img-thumbnail"):
            return _solve_image_captcha(page, context)
        else:
            return True
    else:
        logging.info("Manual captcha required — solve it and press ENTER")
        for _ in range(10):
            notify("ALARM")
        input()
        return True


def _solve_recaptcha(page, context: CustomerProfile):
    site_key = page.get_attribute("#reCAPTCHA_site_key", "value")
    page_action = page.get_attribute("#action", "value")
    logging.info(f"CapSolver: solving reCAPTCHA v3 (site_key={site_key}, action={page_action})")

    try:
        g_response = capsolver_solve_recaptcha_v3(
            api_key=context.capsolver_api_key,
            website_url="https://icp.administracionelectronica.gob.es",
            website_key=site_key,
            page_action=page_action or "",
        )
        logging.info(f"CapSolver: reCAPTCHA solved ({len(g_response)} chars)")
        page.evaluate(f"document.getElementById('g-recaptcha-response').value = '{g_response}'")
        return True
    except CapSolverError as e:
        logging.error(f"CapSolver error: {e}")
        return None


def _solve_image_captcha(page, context: CustomerProfile):
    try:
        img_src = page.get_attribute("img.img-thumbnail", "src")
        img_base64 = img_src.split(",")[1].strip()

        logging.info("CapSolver: solving image captcha")
        captcha_text = capsolver_solve_image(
            api_key=context.capsolver_api_key,
            image_base64=img_base64,
        )
        logging.info(f"CapSolver: image captcha text: {captcha_text}")
        page.fill("#captcha", captcha_text)
        return True
    except CapSolverError as e:
        logging.error(f"CapSolver error: {e}")
        return None
