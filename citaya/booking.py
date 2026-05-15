import atexit
import io
import logging
import os
import random
import re
import signal
import sys
import time
from datetime import datetime as dt

from .browser import (
    PAGE_TIMEOUT,
    get_page_text,
    close_browser,
    close_cookie_banner,
    launch_browser,
)
from .captcha import solve_captcha
from .models import CustomerProfile, DocType, OperationType, Province
from .notify import notify
from .sms import clear_message, wait_for_code

__all__ = ["run"]

DEFAULT_MAX_ATTEMPTS = 144


class WAFBlocked(Exception):
    pass


# ---------------------------------------------------------------------------
# Form filling — step 2 variants
# ---------------------------------------------------------------------------

def _await_form(page, selector="#txtIdCitado"):
    try:
        page.wait_for_selector(selector, timeout=PAGE_TIMEOUT)
        return True
    except Exception:
        logging.error("Timed out waiting for form to load")
        return False


def _click_doc_radio(page, doc_type: DocType):
    if doc_type == DocType.PASSPORT:
        page.click("#rdbTipoDocPas")
    elif doc_type == DocType.NIE:
        page.click("#rdbTipoDocNie")
    elif doc_type == DocType.DNI:
        page.click("#rdbTipoDocDni")


def _fill_doc_fields(page, context: CustomerProfile):
    page.fill("#txtIdCitado", context.doc_value)
    page.fill("#txtDesCitado", context.name)


def _form_expedicion_dggm(page, context: CustomerProfile):
    if not _await_form(page):
        return None
    if context.doc_type == DocType.NIE:
        page.click("#rdbTipoDocNie")
    _fill_doc_fields(page, context)
    return True


def _form_toma_huellas(page, context: CustomerProfile):
    if not _await_form(page, "#txtPaisNac"):
        return None
    page.select_option("#txtPaisNac", label=context.country)
    _click_doc_radio(page, context.doc_type)
    _fill_doc_fields(page, context)
    return True


def _form_recogida(page, context: CustomerProfile):
    if not _await_form(page):
        return None
    _click_doc_radio(page, context.doc_type)
    _fill_doc_fields(page, context)
    return True


def _form_generic(page, context: CustomerProfile):
    if not _await_form(page):
        return None
    _click_doc_radio(page, context.doc_type)
    _fill_doc_fields(page, context)
    return True


def _form_asignacion_nie(page, context: CustomerProfile):
    if not _await_form(page):
        return None
    if context.doc_type == DocType.PASSPORT:
        pas = page.query_selector("#rdbTipoDocPas")
        if pas:
            pas.click()
    _fill_doc_fields(page, context)
    if context.year_of_birth:
        year_field = page.query_selector("#txtAnnoCitado")
        if year_field:
            year_field.fill(context.year_of_birth)
    page.select_option("#txtPaisNac", label=context.country)
    return True


_FORM_HANDLERS = {
    OperationType.EXPEDICION_TARJETAS_DGGM: _form_expedicion_dggm,
    OperationType.TOMA_HUELLAS: _form_toma_huellas,
    OperationType.RECOGIDA_DE_TARJETA: _form_recogida,
    OperationType.ASIGNACION_NIE: _form_asignacion_nie,
}

_GENERIC_OPERATIONS = frozenset([
    OperationType.ASIGNACION_NIE_NO_RESIDENTE,
    OperationType.ASILO_INFORMACION,
    OperationType.ASILO_PRIMERA_CITA,
    OperationType.AUTORIZACION_DE_REGRESO,
    OperationType.BREXIT,
    OperationType.CARTA_INVITACION,
    OperationType.CEDULA_DE_INSCRIPCION,
    OperationType.CERTIFICADO_RESIDENTE,
    OperationType.CERTIFICADOS_CONCORDANCIA,
    OperationType.CERTIFICADOS_NIE,
    OperationType.CERTIFICADOS_NIE_NO_COMUN,
    OperationType.CERTIFICADOS_RESIDENCIA,
    OperationType.CERTIFICADOS_RESIDENCIA_CONCORDANCIA,
    OperationType.CERTIFICADOS_UE,
    OperationType.DECLARACION_ENTRADA,
    OperationType.DOCUMENTOS_ASILO,
    OperationType.INFORMACION_COMISARIA,
    OperationType.PRORROGA_ESTANCIA,
    OperationType.PRORROGA_ESTANCIA_CON_VISADO,
    OperationType.PRORROGA_ESTANCIA_SIN_VISADO,
    OperationType.PROTECCION_TEMPORAL_UCRANIA,
    OperationType.RECOGIDA_CERTIFICADO_REGRESO,
    OperationType.RECOGIDA_TARJETA_ROJA,
    OperationType.RECOGIDA_TIE_DGGM,
    OperationType.SOLICITUD_APATRIDA,
    OperationType.SOLICITUD_ASILO,
    OperationType.TARJETA_ROJA,
    OperationType.TARJETA_UCRANIA,
    OperationType.TITULOS_DE_VIAJE,
    # Extranjería procedures
    OperationType.ARRAIGO_RESIDENCIA,
    OperationType.AUTORIZACION_REGRESO_EXTRANJERIA,
    OperationType.AUTORIZACIONES_TRABAJO,
    OperationType.CIRCUNSTANCIAS_EXCEPCIONALES,
    OperationType.DOCUMENTACION_BRITANICOS,
    OperationType.ESTANCIA_ESTUDIOS,
    OperationType.FAMILIAR_CIUDADANO_ESPAÑOL,
    OperationType.FAMILIAR_ESPAÑOL_RESIDENCIA,
    OperationType.INFORMACION,
    OperationType.MENORES_NACIDOS_ESPAÑA,
    OperationType.MENORES_NO_NACIDOS_ESPAÑA,
    OperationType.MODIFICACION_SITUACIONES,
    OperationType.REAGRUPACION_FAMILIAR,
    OperationType.REAGRUPACION_MENORES_ESTUDIOS,
    OperationType.RECUPERACION_LARGA_DURACION,
    OperationType.REGISTRO,
    OperationType.RENOVACIONES_PRORROGAS,
    OperationType.RENOVACIONES_RESIDENCIA,
    OperationType.TARJETAS_FAMILIAR_UE,
])

_EXTRANJERIA_OPERATIONS = frozenset([
    OperationType.ARRAIGO_RESIDENCIA,
    OperationType.AUTORIZACION_REGRESO_EXTRANJERIA,
    OperationType.AUTORIZACIONES_TRABAJO,
    OperationType.CIRCUNSTANCIAS_EXCEPCIONALES,
    OperationType.DOCUMENTACION_BRITANICOS,
    OperationType.ESTANCIA_ESTUDIOS,
    OperationType.FAMILIAR_CIUDADANO_ESPAÑOL,
    OperationType.FAMILIAR_ESPAÑOL_RESIDENCIA,
    OperationType.INFORMACION,
    OperationType.MENORES_NACIDOS_ESPAÑA,
    OperationType.MENORES_NO_NACIDOS_ESPAÑA,
    OperationType.MODIFICACION_SITUACIONES,
    OperationType.REAGRUPACION_FAMILIAR,
    OperationType.REAGRUPACION_MENORES_ESTUDIOS,
    OperationType.RECUPERACION_LARGA_DURACION,
    OperationType.REGISTRO,
    OperationType.RENOVACIONES_PRORROGAS,
    OperationType.RENOVACIONES_RESIDENCIA,
    OperationType.TARJETAS_FAMILIAR_UE,
])


def _fill_applicant_info(page, context: CustomerProfile):
    handler = _FORM_HANDLERS.get(context.operation_code)
    if handler:
        return handler(page, context)
    if context.operation_code in _GENERIC_OPERATIONS:
        return _form_generic(page, context)
    return None


# ---------------------------------------------------------------------------
# Date/office selection helpers
# ---------------------------------------------------------------------------

def _parse_appointment_date(date_text: str):
    found = re.findall(r"\d{2}/\d{2}/\d{4}", date_text)
    if not found:
        return None
    return dt.strptime(found[0], "%d/%m/%Y")


def _best_matching_date(dates, context: CustomerProfile):
    if not dates:
        return None
    if not context.min_date and not context.max_date:
        return dates[0] if dates else None

    date_format = "%d/%m/%Y"
    min_date = dt.strptime(context.min_date, date_format) if context.min_date else None
    max_date = dt.strptime(context.max_date, date_format) if context.max_date else None
    matches = []

    for date in dates:
        try:
            appt_date = _parse_appointment_date(date)
            if not appt_date:
                continue
            if min_date and appt_date < min_date:
                continue
            if max_date and appt_date > max_date:
                continue
            matches.append((appt_date, date))
        except Exception as e:
            logging.error(e)
            continue

    if matches:
        return min(matches, key=lambda item: item[0])[1]

    logging.info(f"Nothing found for dates {context.min_date} - {context.max_date}, skipping")
    return None


def _best_slot_index(page, context: CustomerProfile):
    try:
        els = page.query_selector_all("[id^=lCita_]")
        dates = [el.text_content() for el in els]
        best_date = _best_matching_date(dates, context)
        if best_date:
            return dates.index(best_date) + 1
    except Exception as e:
        logging.error(e)
    return None


def _pick_office(page, context: CustomerProfile):
    if not context.auto_office:
        notify("MAKE A CHOICE")
        logging.info("Select office and press ENTER")
        input()
        return True

    if context.save_screenshots:
        html = page.inner_html("#idSede")
        offices_path = os.path.join(os.getcwd(), f"offices-{dt.now()}.html".replace(":", "-"))
        with open(offices_path, "w", encoding="utf-8") as f:
            f.write(html)

    if context.offices:
        for office in context.offices:
            try:
                page.select_option("#idSede", value=office.value)
                return True
            except Exception as e:
                logging.error(e)
                if context.operation_code == OperationType.RECOGIDA_DE_TARJETA:
                    return None

    options = page.evaluate("""
        Array.from(document.querySelector('#idSede').options)
            .filter(o => o.value !== '')
            .map(o => o.value)
    """)
    if not options:
        return None

    excluded = [o.value for o in context.except_offices] if context.except_offices else []
    for _ in range(5):
        pick = random.choice(options)
        if pick not in excluded:
            page.select_option("#idSede", value=pick)
            return True

    return None


def _submit_office(page, context: CustomerProfile):
    try:
        page.wait_for_function("typeof enviar === 'function'", timeout=PAGE_TIMEOUT)
    except Exception:
        logging.error("enviar() JS function never appeared on page")
        return None

    page.evaluate("enviar('solicitud');")
    time.sleep(random.uniform(2, 4))

    resp_text = get_page_text(page)

    if "Seleccione la oficina donde solicitar la cita" in resp_text:
        logging.info("[office] Selecting office")
        try:
            page.wait_for_selector("#btnSiguiente", timeout=PAGE_TIMEOUT)
        except Exception:
            logging.error("Timed out waiting for offices to load")
            return None

        res = _pick_office(page, context)
        if res is None:
            return None

        page.click("#btnSiguiente")
        return True
    elif "En este momento no hay citas disponibles" in resp_text:
        logging.info("[office] No appointments available — will retry")
        return None
    else:
        logging.info(f"[office] Unexpected response: {resp_text[:200]}")
        if context.save_screenshots:
            page.screenshot(path=f"office-unexpected-{dt.now()}.png".replace(":", "-"))
        return None


# ---------------------------------------------------------------------------
# Contact info & cita selection (steps 3-6)
# ---------------------------------------------------------------------------

def _submit_contact(page, context: CustomerProfile):
    try:
        page.wait_for_selector("#txtTelefonoCitado", timeout=PAGE_TIMEOUT)
        logging.info("[contact] Submitting contact details")
    except Exception:
        logging.error("Timed out waiting for contact info page")
        return None

    page.fill("#txtTelefonoCitado", context.phone)

    try:
        page.fill("#emailUNO", context.email)
        page.fill("#emailDOS", context.email)
    except Exception:
        pass

    page.evaluate("enviar();")
    time.sleep(random.uniform(2, 4))

    return _select_slot(page, context)


def _select_slot(page, context: CustomerProfile):
    resp_text = get_page_text(page)

    if "DISPONE DE 5 MINUTOS" in resp_text:
        logging.info("[slot] Available slots found!")
        if context.save_screenshots:
            page.screenshot(path=f"citas-{dt.now()}.png".replace(":", "-"))

        position = _best_slot_index(page, context)
        if not position:
            return None

        time.sleep(2)
        if not solve_captcha(page, context):
            return None

        radios = page.query_selector_all("input[type='radio'][name='rdbCita']")
        if position - 1 < len(radios):
            radios[position - 1].click()

        page.evaluate("envia();")
        time.sleep(1)

    elif "Seleccione una de las siguientes citas disponibles" in resp_text:
        logging.info("[slot] Available slots found!")
        if context.save_screenshots:
            page.screenshot(path=f"citas-{dt.now()}.png".replace(":", "-"))

        try:
            slots = page.evaluate("""() => {
                const headers = document.querySelectorAll('#CitaMAP_HORAS thead [class^=colFecha]');
                const dates = Array.from(headers).map(h => h.textContent.trim());
                const result = {};
                const rows = document.querySelectorAll('#CitaMAP_HORAS tbody tr');
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    cells.forEach((cell, idx) => {
                        if (dates[idx] && !result[dates[idx]]) {
                            const hueco = cell.querySelector('[id^=HUECO]');
                            if (hueco) result[dates[idx]] = hueco.id;
                        }
                    });
                });
                return result;
            }""")

            best_date = _best_matching_date(list(slots.keys()), context)
            if not best_date:
                return None
            slot = slots[best_date]

            time.sleep(2)
            if not solve_captcha(page, context):
                return None

            page.evaluate(f"confirmarHueco({{id: '{slot}'}}, {slot[5:]});")
            time.sleep(1)
        except Exception as e:
            logging.error(e)
            return None
    else:
        logging.info("[slot] No slots in response")
        return None

    # Confirmation
    time.sleep(2)
    resp_text = get_page_text(page)

    if "Debe confirmar los datos de la cita asignada" in resp_text:
        logging.info("[confirm] Confirmation page reached")

        sms_field = page.query_selector("#txtCodigoVerificacion")

        if context.sms_webhook_token:
            if sms_field:
                code = wait_for_code(context)
                if code:
                    logging.info(f"Received SMS code: {code}")
                    page.fill("#txtCodigoVerificacion", code)

            return _confirm(page, context)
        else:
            if not sms_field:
                return _confirm(page, context)

            notify("ENTER THE SHORT CODE FROM SMS")
            logging.info("SMS verification needed — enter code manually and press ENTER")
            input()
            return _confirm(page, context)
    else:
        logging.info("[confirm] Missed confirmation page")
        if context.save_screenshots:
            page.screenshot(path=f"failed-confirmation-{dt.now()}.png".replace(":", "-"))
        return None


def _confirm(page, context: CustomerProfile):
    page.click("#chkTotal")
    page.click("#enviarCorreo")
    page.click("#btnConfirmar")
    time.sleep(2)

    resp_text = get_page_text(page)
    ctime = dt.now()

    if "CITA CONFIRMADA Y GRABADA" in resp_text:
        context.booked = True
        code = page.text_content("#justificanteFinal")
        logging.info(f"[done] Booking reference: {code}")
        if context.save_screenshots:
            page.screenshot(path=f"CONFIRMED-CITA-{ctime}.png".replace(":", "-"))
        return True
    elif "Lo sentimos, el código introducido no es correcto" in resp_text:
        logging.error("Incorrect SMS code entered")
    else:
        if context.save_screenshots:
            page.screenshot(path=f"error-{ctime}.png".replace(":", "-"))

    return None


# ---------------------------------------------------------------------------
# Main cycle
# ---------------------------------------------------------------------------

def _attempt_booking(page, context: CustomerProfile, url1: str, url2: str):
    time.sleep(random.uniform(1, 3))
    try:
        page.goto(url1, timeout=60000, wait_until="domcontentloaded")
    except Exception as e:
        if "has been closed" in str(e):
            raise  # bubble up so run() restarts the browser
        logging.error(f"Failed to load url1: {e}")
        return None
    time.sleep(random.uniform(2, 4))

    try:
        page.goto(url2, timeout=60000, wait_until="domcontentloaded")
    except Exception as e:
        if "has been closed" in str(e):
            raise
        logging.error(f"Failed to load url2: {e}")
        return None

    logging.info("Waiting for ICP page to load (WAF challenge may run)...")
    try:
        page.wait_for_selector("#btnEntrar", timeout=60000)
    except Exception:
        resp_text = get_page_text(page)
        if "Too Many Requests" in resp_text:
            logging.warning("Rate limited (429) — backing off")
            time.sleep(random.uniform(30, 60))
            return None
        elif "requested URL was rejected" in resp_text:
            logging.warning("WAF hard-block on initial load")
            raise WAFBlocked("WAF blocked on initial load")
        else:
            logging.error(f"Page did not load #btnEntrar within 60s (body: {resp_text[:150]})")
            if context.save_screenshots:
                page.screenshot(path=f"load-fail-{dt.now()}.png".replace(":", "-"))
            return None

    logging.info("ICP page loaded — #btnEntrar found")

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    cookies = page.context.cookies()
    cookie_names = [c["name"] for c in cookies]
    logging.info(f"Cookies before Entrar: {cookie_names}")

    close_cookie_banner(page)

    page.evaluate("window.scrollBy(0, Math.floor(Math.random() * 150 + 50))")
    time.sleep(random.uniform(3, 6))
    page.click("#btnEntrar")

    try:
        page.wait_for_selector("#txtIdCitado, #txtPaisNac, #btnEnviar", timeout=60000)
    except Exception:
        resp_text = get_page_text(page)
        if "requested URL was rejected" in resp_text:
            logging.warning(f"WAF blocked after Entrar (url: {page.url})")
            if context.save_screenshots:
                page.screenshot(path=f"waf-block-{dt.now()}.png".replace(":", "-"))
            raise WAFBlocked("WAF blocked after Entrar")
        else:
            logging.error(f"Form page did not load after Entrar (body: {resp_text[:150]})")
            return None

    logging.info("Form page loaded after Entrar")

    page.on("dialog", lambda d: d.accept())

    logging.info("[applicant-info] Filling personal details")
    success = _fill_applicant_info(page, context)

    if not success:
        return None

    time.sleep(random.uniform(1, 2))
    page.click("#btnEnviar")
    time.sleep(random.uniform(3, 5))

    resp_text = get_page_text(page)
    if "no hay citas disponibles" in resp_text:
        logging.info("[office] No appointments available — will retry")
        return "NO_CITAS"

    if context.wait_exact_time:
        logging.info("Waiting for exact time...")
        while [dt.now().minute, dt.now().second] not in context.wait_exact_time:
            time.sleep(0.5)

    selection_result = _submit_office(page, context)
    if selection_result is None:
        return None

    return _submit_contact(page, context)


_SINGLE_GROUP_PROVINCES = frozenset([
    Province.BARCELONA,
    Province.MADRID,
    Province.MELILLA,
    Province.SEVILLA,
    Province.VALENCIA,
])


def _build_target_urls(context: CustomerProfile):
    operation_category = "icpplus"

    if context.province == Province.BARCELONA:
        operation_category = "icpplustieb"
    elif context.province in [Province.ALICANTE, Province.ILLES_BALEARS, Province.LAS_PALMAS, Province.S_CRUZ_TENERIFE]:
        operation_category = "icpco"
    elif context.province == Province.MADRID:
        operation_category = "icpplustiem"
    elif context.province == Province.MÁLAGA:
        operation_category = "icpplustiem"

    if context.province in _SINGLE_GROUP_PROVINCES:
        operation_param = "tramiteGrupo[0]"
    elif context.operation_code in _EXTRANJERIA_OPERATIONS:
        operation_param = "tramiteGrupo[0]"
    else:
        operation_param = "tramiteGrupo[1]"

    base = "https://icp.administracionelectronica.gob.es"
    url1 = f"{base}/{operation_category}/citar?p={context.province.value}"
    url2 = f"{base}/{operation_category}/acInfo?{operation_param}={context.operation_code.value}"
    return url1, url2


def run(context: CustomerProfile, max_attempts: int = DEFAULT_MAX_ATTEMPTS):
    browser_ref = [None]

    def _cleanup_on_signal(signum, frame):
        logging.info(f"Received signal {signum} — cleaning up")
        if browser_ref[0]:
            close_browser(browser_ref[0])
        sys.exit(1)

    signal.signal(signal.SIGTERM, _cleanup_on_signal)
    atexit.register(lambda: close_browser(browser_ref[0]) if browser_ref[0] else None)

    if context.sms_webhook_token:
        clear_message(context.sms_webhook_token)

    url1, url2 = _build_target_urls(context)
    logging.info(f"Target: {url2}")

    browser = None
    page = None

    for i in range(max_attempts):
        try:
            if browser is None:
                logging.info("Launching Chrome via CDP...")
                browser = launch_browser(context)
                browser_ref[0] = browser
                contexts = browser.contexts
                if contexts and contexts[0].pages:
                    page = contexts[0].pages[0]
                else:
                    page = browser.new_page()

            logging.info(f"\033[33m[Attempt {i + 1}/{max_attempts}]\033[0m")
            result = _attempt_booking(page, context, url1, url2)

            if result is True:
                logging.info("\033[32mWIN — Appointment booked!\033[0m")
                if context.save_screenshots:
                    page.screenshot(path=f"WIN-{dt.now()}.png".replace(":", "-"))
                close_browser(browser)
                return True

            try:
                page.goto("about:blank")
            except Exception:
                pass

            if result == "NO_CITAS":
                delay = random.uniform(28, 35)
            else:
                delay = random.uniform(45, 75)
            logging.info(f"Waiting {delay:.0f}s before next attempt")
            time.sleep(delay)

        except KeyboardInterrupt:
            logging.info("Interrupted by user")
            close_browser(browser)
            raise
        except WAFBlocked:
            logging.info("WAF block — restarting browser with fresh session")
            close_browser(browser)
            browser = None
            browser_ref[0] = None
            page = None
            waf_delay = random.uniform(180, 240)
            logging.info(f"WAF cooldown: waiting {waf_delay:.0f}s")
            time.sleep(waf_delay)
            continue
        except Exception as e:
            if "has been closed" in str(e):
                logging.info("Browser was closed (mac locked / chrome crashed?) — restarting")
            else:
                logging.error(f"Error: {e}")
            close_browser(browser)
            browser = None
            browser_ref[0] = None
            page = None
            time.sleep(random.uniform(5, 10))
            continue

    logging.error("All attempts exhausted — FAIL")
    notify("FAIL")
    close_browser(browser)
    return False
