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
    selector = None
    if doc_type == DocType.PASSPORT:
        selector = "#rdbTipoDocPas"
    elif doc_type == DocType.NIE:
        selector = "#rdbTipoDocNie"
    elif doc_type == DocType.DNI:
        selector = "#rdbTipoDocDni"

    if selector:
        page.locator(selector).click()
        time.sleep(random.uniform(0.5, 1.2))


def _move_mouse_to_element(page, selector: str):
    box = page.locator(selector).bounding_box()
    if box:
        x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
        y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
        page.mouse.move(x, y, steps=random.randint(8, 20))
        time.sleep(random.uniform(0.1, 0.3))


def _human_pause():
    time.sleep(random.uniform(1.0, 2.5))


def _type_like_user(page, selector: str, value: str, delay_min: int = 70, delay_max: int = 140):
    locator = page.locator(selector)
    locator.scroll_into_view_if_needed()
    time.sleep(random.uniform(0.3, 0.7))
    _move_mouse_to_element(page, selector)
    locator.click()
    time.sleep(random.uniform(0.3, 0.8))
    page.keyboard.press("ControlOrMeta+A")
    page.keyboard.press("Backspace")
    time.sleep(random.uniform(0.1, 0.3))
    page.keyboard.type(value, delay=random.randint(delay_min, delay_max))
    time.sleep(random.uniform(0.7, 1.4))


def _fill_doc_fields(page, context: CustomerProfile):
    _type_like_user(page, "#txtIdCitado", context.doc_value.upper(), 90, 160)
    _human_pause()
    _type_like_user(page, "#txtDesCitado", context.name.upper(), 80, 140)


def _select_country(page, context: CustomerProfile):
    _human_pause()
    _move_mouse_to_element(page, "#txtPaisNac")
    time.sleep(random.uniform(0.3, 0.6))
    try:
        page.select_option("#txtPaisNac", label=context.country)
    except Exception:
        option_value = page.evaluate("""(country) => {
            const normalize = (value) => (value || "")
                .normalize("NFD")
                .replace(/[\\u0300-\\u036f]/g, "")
                .trim()
                .toUpperCase();
            const expected = normalize(country);
            const option = Array.from(document.querySelectorAll("#txtPaisNac option"))
                .find((item) => normalize(item.textContent) === expected);
            return option ? option.value : null;
        }""", context.country)
        if not option_value:
            logging.error(f"Could not find nationality option: {context.country}")
            return None
        page.select_option("#txtPaisNac", value=option_value)

    selected = page.evaluate("""() => {
        const select = document.querySelector("#txtPaisNac");
        return select?.selectedOptions?.[0]?.textContent?.trim() || "";
    }""")
    logging.info(f"[applicant-info] Nationality selected: {selected}")
    page.locator("#txtPaisNac").blur()
    time.sleep(random.uniform(1.2, 2.4))
    return True


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
    if not _await_form(page, "#txtIdCitado"):
        return None
    _click_doc_radio(page, context.doc_type)
    _fill_doc_fields(page, context)
    return _select_country(page, context)


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
    return _select_country(page, context)


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
        if not dates:
            dates = _slot_texts_from_radios(page)
        best_date = _best_matching_date(dates, context)
        if best_date:
            return dates.index(best_date) + 1
    except Exception as e:
        logging.error(e)
    return None


def _slot_texts_from_radios(page):
    return page.evaluate("""() => {
        const radios = Array.from(document.querySelectorAll("input[type='radio'][name='rdbCita']"));
        return radios.map((radio) => {
            let node = radio.closest("label") || radio.closest("td") || radio.closest("div") || radio.parentElement;
            while (node && node.parentElement) {
                const text = (node.innerText || node.textContent || "").trim();
                if (/\\d{2}\\/\\d{2}\\/\\d{4}/.test(text) || /D[ií]a\\s*:/i.test(text)) {
                    return text;
                }
                node = node.parentElement;
            }
            return (radio.value || "").trim();
        });
    }""")


def _has_five_minute_slot_page(resp_text: str):
    upper_text = resp_text.upper()
    return "DISPONE DE 5 MINUTOS" in upper_text or "DISPONES DE 5 MINUTOS" in upper_text


def _save_debug_page(page, context: CustomerProfile, prefix: str):
    if not context.save_screenshots:
        return

    path_prefix = f"{prefix}-{dt.now()}".replace(":", "-")
    try:
        page.screenshot(path=f"{path_prefix}.png", full_page=True)
    except Exception as e:
        logging.error(f"Could not save debug screenshot: {e}")

    try:
        with open(f"{path_prefix}.html", "w", encoding="utf-8") as f:
            f.write(page.content())
    except Exception as e:
        logging.error(f"Could not save debug HTML: {e}")


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
    resp_text = get_page_text(page)
    if _is_identity_action_page(resp_text) or _has_solicitar_cita_control(page):
        logging.info("[identity] Requesting appointment")
        if not _click_solicitar_cita(page):
            return None
        time.sleep(random.uniform(2, 4))
        resp_text = get_page_text(page)
    elif not _is_office_selection_page(page, resp_text):
        try:
            page.wait_for_function("typeof enviar === 'function'", timeout=PAGE_TIMEOUT)
        except Exception:
            if "requested URL was rejected" in resp_text:
                logging.warning(f"WAF blocked after applicant form (url: {page.url})")
                _save_debug_page(page, context, "waf-after-applicant")
                raise WAFBlocked("WAF blocked after applicant form")
            logging.error(f"[post-applicant] Unexpected page before office selection: {resp_text[:300]}")
            _save_debug_page(page, context, "post-applicant-unexpected")
            return None

        page.evaluate("enviar('solicitud');")
        time.sleep(random.uniform(2, 4))
        resp_text = get_page_text(page)

    if _is_office_selection_page(page, resp_text):
        logging.info("[office] Selecting office")
        try:
            page.wait_for_selector("#btnSiguiente", timeout=PAGE_TIMEOUT)
        except Exception:
            logging.error("Timed out waiting for offices to load")
            return None

        if page.query_selector("#idSede"):
            res = _pick_office(page, context)
            if res is None:
                return None
        else:
            logging.info("[office] Office already selected by site")

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


def _is_identity_action_page(resp_text: str):
    text = resp_text.lower()
    return "identidad del usuario de cita" in text and (
        "solicitar cita" in text
        or "consultar citas confirmadas" in text
        or "anular cita" in text
    )


def _has_solicitar_cita_control(page):
    try:
        return bool(page.evaluate("""() => {
            const buttonLike = "input[type='button'], input[type='submit'], button, a, [role='button']";
            const clickHandlers = "div[onclick], span[onclick], li[onclick]";
            return [
                ...Array.from(document.querySelectorAll(buttonLike)),
                ...Array.from(document.querySelectorAll(clickHandlers)),
            ].some((el) => {
                const label = ((el.value || el.innerText || el.textContent || "") + "").trim();
                return /Solicitar\\s+Cita/i.test(label);
            });
        }"""))
    except Exception:
        return False


def _click_solicitar_cita(page):
    try:
        clicked = page.evaluate("""() => {
            const buttonLike = "input[type='button'], input[type='submit'], button, a, [role='button']";
            const clickHandlers = "div[onclick], span[onclick], li[onclick]";
            const candidates = [
                ...Array.from(document.querySelectorAll(buttonLike)),
                ...Array.from(document.querySelectorAll(clickHandlers)),
            ];
            const match = candidates.find((el) => {
                const label = ((el.value || el.innerText || el.textContent || "") + "").trim();
                return /Solicitar\\s+Cita/i.test(label);
            });
            if (!match) return false;
            match.scrollIntoView({ block: "center", inline: "center" });
            match.click();
            return true;
        }""")
        if clicked:
            return True
    except Exception as e:
        logging.error(f"[identity] Could not click Solicitar Cita: {e}")

    try:
        page.evaluate("enviar('solicitud');")
        return True
    except Exception as e:
        logging.error(f"[identity] Could not request appointment: {e}")
        return False


def _is_office_selection_page(page, resp_text: str):
    return (
        "Seleccione la oficina donde solicitar la cita" in resp_text
        or "Selecciona Oficina" in resp_text
        or bool(page.query_selector("#idSede"))
    )


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

    time.sleep(random.uniform(2, 4))
    _type_like_user(page, "#txtTelefonoCitado", context.phone, 80, 140)

    try:
        _type_like_user(page, "#emailUNO", context.email, 45, 95)
        _type_like_user(page, "#emailDOS", context.email, 45, 95)
    except Exception:
        pass

    _save_debug_page(page, context, "contact-filled")
    time.sleep(random.uniform(2, 4))
    page.locator("input[value='Siguiente'], #btnSiguiente").first.click()
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass
    time.sleep(random.uniform(2, 4))

    return _select_slot(page, context)


def _select_slot(page, context: CustomerProfile):
    resp_text = get_page_text(page)

    if _has_five_minute_slot_page(resp_text):
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
        logging.info(f"[slot] No slots in response (body: {resp_text[:300]})")
        _save_debug_page(page, context, "slot-unrecognized")
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
        _open_operation_info(page, context, url1, url2)
    except Exception as e:
        if "has been closed" in str(e):
            raise  # bubble up so run() restarts the browser
        logging.error(f"Failed to load operation info page: {e}")
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

    logging.info("ICP page loaded — sin Cl@ve option (#btnEntrar) found")

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    for _ in range(random.randint(2, 4)):
        page.mouse.move(random.randint(100, 700), random.randint(150, 400), steps=random.randint(5, 15))
        time.sleep(random.uniform(0.5, 1.5))

    cookies = page.context.cookies()
    cookie_names = [c["name"] for c in cookies]
    logging.info(f"Cookies before Entrar: {cookie_names}")

    close_cookie_banner(page)

    page.mouse.wheel(0, random.randint(80, 200))
    time.sleep(random.uniform(3, 6))
    _move_mouse_to_element(page, "#btnEntrar")
    time.sleep(random.uniform(0.3, 0.8))
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
            _save_debug_page(page, context, "form-load-fail-after-entrar")
            return None

    logging.info("Form page loaded after Entrar")

    page.on("dialog", lambda d: d.accept())

    for _ in range(random.randint(2, 4)):
        page.mouse.move(random.randint(200, 600), random.randint(200, 500), steps=random.randint(5, 15))
        time.sleep(random.uniform(0.8, 2.0))
    time.sleep(random.uniform(1, 3))
    logging.info("[applicant-info] Filling personal details")
    success = _fill_applicant_info(page, context)

    if not success:
        return None

    _save_debug_page(page, context, "applicant-filled")
    time.sleep(random.uniform(4, 7))
    page.mouse.wheel(0, random.randint(50, 150))
    time.sleep(random.uniform(2, 4))
    page.locator("#btnEnviar").scroll_into_view_if_needed()
    _move_mouse_to_element(page, "#btnEnviar")
    time.sleep(random.uniform(0.5, 1.2))
    page.locator("#btnEnviar").click()
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass
    time.sleep(random.uniform(3, 5))

    resp_text = get_page_text(page)
    if "no hay citas disponibles" in resp_text.lower():
        logging.info("[applicant-info] Server returned no appointments immediately after applicant form")
        _save_debug_page(page, context, "no-citas-after-applicant")
        return "NO_CITAS"
    _save_debug_page(page, context, "post-applicant")

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

    operation_param = _operation_param_name(context)

    base = "https://icp.administracionelectronica.gob.es"
    url1 = f"{base}/{operation_category}/citar?p={context.province.value}"
    url2 = f"{base}/{operation_category}/acInfo?{operation_param}={context.operation_code.value}"
    return url1, url2


def _operation_param_name(context: CustomerProfile):
    if context.province in _SINGLE_GROUP_PROVINCES:
        return "tramiteGrupo[0]"
    if context.operation_code in _EXTRANJERIA_OPERATIONS:
        return "tramiteGrupo[0]"
    return "tramiteGrupo[1]"


def _open_operation_info(page, context: CustomerProfile, url1: str, url2: str):
    page.goto(url1, timeout=60000, wait_until="domcontentloaded")
    time.sleep(random.uniform(2, 4))
    close_cookie_banner(page)

    if _submit_operation_from_portada(page, context):
        time.sleep(random.uniform(2, 4))
        return True

    logging.info("[operation] Falling back to direct operation URL")
    page.goto(url2, timeout=60000, wait_until="domcontentloaded")
    time.sleep(random.uniform(2, 4))
    close_cookie_banner(page)
    return True


def _submit_operation_from_portada(page, context: CustomerProfile):
    operation_param = _operation_param_name(context)
    selector = f"select[name='{operation_param}']"

    try:
        page.wait_for_selector(selector, timeout=PAGE_TIMEOUT)
    except Exception:
        logging.info("[operation] Procedure selector not found on province page")
        return False

    try:
        logging.info(f"[operation] Selecting {operation_param}={context.operation_code.value}")
        page.select_option(selector, value=context.operation_code.value)
    except Exception as e:
        logging.error(f"[operation] Procedure option unavailable: {e}")
        return False

    try:
        if context.save_screenshots:
            page.screenshot(path=f"operation-selected-{dt.now()}.png".replace(":", "-"))

        if page.query_selector("#btnAceptar"):
            page.click("#btnAceptar")
        else:
            page.evaluate("envia();")
        return True
    except Exception as e:
        logging.error(f"[operation] Failed to submit procedure selection: {e}")
        return False


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

            if i == max_attempts - 1:
                break

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
