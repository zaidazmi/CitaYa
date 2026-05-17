<div align="center">

# CitaYa

**Stop refreshing. Start booking.**

Automated *cita previa* booking for Spanish immigration offices.\
Runs 24/7 on your machine until it locks down your appointment.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776ab?logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/playwright-CDP-2ead33?logo=playwright&logoColor=white)](https://playwright.dev)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)

</div>

---

> **Not a developer?** Paste this repo link into [ChatGPT](https://chat.openai.com), [Claude](https://claude.ai), or any AI assistant and ask:\
> *"Help me set this up on my computer to book a cita previa."*\
> It will walk you through every step.

---

## Why CitaYa?

Anyone who has tried to book a *cita previa* knows the pain: slots appear for seconds, the site crashes under load, and refreshing manually for hours is soul-crushing. CitaYa watches the site for you around the clock and books the moment a slot opens.

**How it works:**

```
Chrome (real browser)  -->  Playwright via CDP  -->  ICP appointment site
       |                         |                         |
  F5 WAF sees a                Fills forms,           Polls every ~30s,
  genuine session              solves captcha         grabs first slot
```

1. Launches **your real Chrome** with remote debugging
2. Playwright connects via CDP — the WAF sees a genuine browser session
3. Selects the province procedure, enters through **sin Cl@ve**, and fills your personal info
4. Polls for available slots (~30s between checks)
5. Handles province-specific intermediate pages like **Solicitar Cita** and preselected offices
6. When a slot appears: fills contact details, solves captcha, selects the slot, confirms booking
7. Saves a screenshot of the confirmation

### Why real Chrome?

The ICP site runs **F5 Shape Security** which fingerprints the browser deeply — TLS handshake, JS engine, canvas, WebGL. Headless browsers get caught. Real Chrome via CDP passes because F5 sees an authentic browser with matching fingerprints.

## Quick start

### Prerequisites

| Requirement | Notes |
|:--|:--|
| **Python 3.10+** | |
| **Google Chrome** | The real browser, not Chromium |
| **[CapSolver](https://www.capsolver.com/) API key** | For automatic captcha solving |

### Install

```bash
git clone https://github.com/zaidazmi/CitaYa.git
cd CitaYa
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Run

```bash
cp example.py my_appointment.py
```

Edit `my_appointment.py` with your details:

```python
from citaya import CustomerProfile, DocType, OperationType, Province, run

customer = CustomerProfile(
    capsolver_api_key="YOUR-CAPSOLVER-API-KEY",
    province=Province.BARCELONA,
    operation_code=OperationType.TOMA_HUELLAS,
    doc_type=DocType.NIE,
    doc_value="Y1234567X",
    country="INDIA",
    name="Your Name",
    phone="600000000",
    email="you@example.com",
)

if __name__ == "__main__":
    run(context=customer, max_attempts=200)
```

```bash
python3 -u my_appointment.py
```

A Chrome window opens and the bot starts polling. Leave it running.

## Configuration

### Required fields

| Field | Description |
|:--|:--|
| `name` | Full name (first and last) |
| `doc_type` | `DocType.NIE`, `DocType.PASSPORT`, or `DocType.DNI` |
| `doc_value` | Document number (no spaces) |
| `phone` | Phone number, e.g. `"600000000"` |
| `email` | Email address |
| `province` | `Province.BARCELONA`, `Province.MADRID`, etc. |
| `operation_code` | Procedure type (see supported procedures below) |
| `country` | Country name as shown on the ICP site (e.g. `"INDIA"`, `"MARRUECOS"`) |

### Optional fields

| Field | Default | Description |
|:--|:--|:--|
| `capsolver_api_key` | `None` | CapSolver API key for auto captcha |
| `auto_captcha` | `True` | Solve captchas automatically |
| `auto_office` | `True` | Auto-select available office |
| `chrome_path` | auto-detect | Path to Chrome binary |
| `headless` | `False` | Run Chrome in headless mode |
| `save_screenshots` | `False` | Save screenshots on events |
| `offices` | `[]` | Specific offices to try (`Office` enum values) |
| `except_offices` | `[]` | Offices to exclude |
| `min_date` | `None` | Skip dates before this (`"dd/mm/yyyy"`) |
| `max_date` | `None` | Skip dates after this (`"dd/mm/yyyy"`) |
| `year_of_birth` | `None` | Required for some procedures |
| `sms_webhook_token` | `None` | For auto SMS verification (see below) |
| `wait_exact_time` | `None` | `[[minute, second]]` — submit at exact time |

## SMS auto-verification

Some appointments require SMS confirmation. To automate this:

1. Get a token from [webhook.site](https://webhook.site)
2. Set `sms_webhook_token` in your config
3. Use [IFTTT](https://ifttt.com/) on your phone: when SMS contains "CITA PREVIA", forward to your webhook.site email

## Supported procedures

All Spanish provinces are supported. Procedures have been verified against the live ICP site for **Barcelona, Madrid, Valencia, Malaga, Alicante, Sevilla, and Zaragoza**. Other provinces use the same system and should work, but procedure availability varies.

<details>
<summary><strong>Police procedures (Policia Nacional)</strong> — 32 procedures</summary>

| Code | Procedure |
|:--|:--|
| `TOMA_HUELLAS` | Toma de huellas (expedicion de tarjeta) |
| `EXPEDICION_TARJETAS_DGGM` | Expedicion de tarjetas (Direccion General de Gestion Migratoria) |
| `RECOGIDA_DE_TARJETA` | Recogida de tarjeta de identidad de extranjero (TIE) |
| `RECOGIDA_TIE_DGGM` | Recogida de la TIE cuya autorizacion resuelve la DGGM |
| `RECOGIDA_TARJETA_ROJA` | Recogida de tarjeta roja (proteccion internacional) |
| `RECOGIDA_CERTIFICADO_REGRESO` | Recogida certificado y autorizacion de regreso |
| `AUTORIZACION_DE_REGRESO` | Autorizacion de regreso |
| `ASIGNACION_NIE` | Asignacion de NIE |
| `ASIGNACION_NIE_NO_RESIDENTE` | Asignacion NIE no residente no comunitario |
| `CARTA_INVITACION` | Carta de invitacion |
| `CERTIFICADO_RESIDENTE` | Certificado de residente o no residente |
| `CERTIFICADOS_CONCORDANCIA` | Certificados concordancia |
| `CERTIFICADOS_NIE` | Certificados y asignacion NIE |
| `CERTIFICADOS_NIE_NO_COMUN` | Certificados y asignacion NIE (no comunitarios) |
| `CERTIFICADOS_RESIDENCIA` | Certificados (residencia, no residencia, concordancia) |
| `CERTIFICADOS_RESIDENCIA_CONCORDANCIA` | Certificados (residencia y concordancia) |
| `CERTIFICADOS_UE` | Certificado de registro de ciudadano de la U.E. |
| `CEDULA_DE_INSCRIPCION` | Cedula de inscripcion |
| `DOCUMENTOS_ASILO` | Expedicion/renovacion de documentos de solicitantes de asilo |
| `SOLICITUD_ASILO` | Solicitud de asilo |
| `ASILO_INFORMACION` | Asilo informacion |
| `ASILO_PRIMERA_CITA` | Asilo — primera cita |
| `SOLICITUD_APATRIDA` | Solicitud de apatrida |
| `TARJETA_ROJA` | Documento acreditativo proteccion internacional (tarjeta roja) |
| `TARJETA_UCRANIA` | Tarjeta conflicto Ucrania |
| `PROTECCION_TEMPORAL_UCRANIA` | Solicitud proteccion temporal desplazados Ucrania |
| `BREXIT` | Expedicion tarjeta Brexit |
| `TITULOS_DE_VIAJE` | Titulos de viaje |
| `PRORROGA_ESTANCIA` | Prorroga de estancia |
| `PRORROGA_ESTANCIA_CON_VISADO` | Prorroga de estancia con visado |
| `PRORROGA_ESTANCIA_SIN_VISADO` | Prorroga de estancia sin visado |
| `DECLARACION_ENTRADA` | Declaracion de entrada |
| `INFORMACION_COMISARIA` | Informacion de tramites de la comisaria de policia |

</details>

<details>
<summary><strong>Extranjeria procedures (Oficinas de Extranjeria)</strong> — 19 procedures</summary>

Available in provinces with extranjeria offices (e.g. Alicante, Malaga, Zaragoza).

| Code | Procedure |
|:--|:--|
| `ARRAIGO_RESIDENCIA` | Autorizaciones de residencia temporal por motivos de arraigo |
| `AUTORIZACION_REGRESO_EXTRANJERIA` | Autorizacion de regreso (extranjeria) |
| `AUTORIZACIONES_TRABAJO` | Autorizaciones de trabajo, renovaciones, prorrogas y modificaciones |
| `CIRCUNSTANCIAS_EXCEPCIONALES` | Autorizaciones de residencia por circunstancias excepcionales |
| `DOCUMENTACION_BRITANICOS` | Documentacion de nacionales del Reino Unido (Brexit) |
| `ESTANCIA_ESTUDIOS` | Estancia por estudios |
| `FAMILIAR_CIUDADANO_ESPAÑOL` | Familiar de ciudadano español |
| `FAMILIAR_ESPAÑOL_RESIDENCIA` | Residencia temporal de familiares de personas con nacionalidad española |
| `INFORMACION` | Informacion |
| `MENORES_NACIDOS_ESPAÑA` | Autorizacion de residencia de menores nacidos en España |
| `MENORES_NO_NACIDOS_ESPAÑA` | Autorizacion de residencia de menores no nacidos en España |
| `MODIFICACION_SITUACIONES` | Modificacion de las situaciones |
| `REAGRUPACION_FAMILIAR` | Autorizacion de residencia temporal por reagrupacion familiar |
| `REAGRUPACION_MENORES_ESTUDIOS` | Reagrupacion inicial, menores y estancia por estudios inicial |
| `RECUPERACION_LARGA_DURACION` | Recuperacion de la autorizacion de larga duracion |
| `REGISTRO` | Registro |
| `RENOVACIONES_PRORROGAS` | Renovaciones, prorrogas y modificaciones |
| `RENOVACIONES_RESIDENCIA` | Renovaciones de residencia |
| `TARJETAS_FAMILIAR_UE` | Tarjetas de familiares de ciudadanos de la Union Europea |

</details>

## Troubleshooting

<details>
<summary><strong>Logs not appearing in real-time?</strong></summary>

Run with `python3 -u` (unbuffered output).
</details>

<details>
<summary><strong>WAF blocking?</strong></summary>

The bot auto-detects WAF blocks, restarts the browser with a fresh session, and backs off 3-4 minutes before retrying. No action needed.
</details>

<details>
<summary><strong>Rate limited (429)?</strong></summary>

Auto-detected — the bot backs off 30-60 seconds.
</details>

<details>
<summary><strong>Manual flow shows appointments, but the bot says no citas?</strong></summary>

Make sure you are on the latest code and run with `save_screenshots=True`. Some provinces, including Salamanca for `TOMA_HUELLAS`, show extra pages after the applicant form:

1. `Identidad del usuario de cita` with a `Solicitar Cita` button
2. `Selecciona Oficina`, sometimes with the office already selected
3. Contact details
4. Slot and captcha page

CitaYa handles this flow, but screenshots are the fastest way to confirm where the site diverged. Also check that `province`, `operation_code`, `doc_type`, and `country` exactly match the manual flow.
</details>

<details>
<summary><strong>Port 9222 in use?</strong></summary>

Kill stale Chrome: `pkill -f "remote-debugging-port=9222"`
</details>

<details>
<summary><strong>Certificate errors in your normal browser?</strong></summary>

The bot uses a separate Chrome profile (`~/.chrome-citaya`). Your regular Chrome is unaffected.
</details>

<details>
<summary><strong>Chrome not found?</strong></summary>

The bot auto-detects Chrome on macOS, Linux, and Windows. If detection fails, set `chrome_path` in your `CustomerProfile`.
</details>

## Contributing

Contributions are welcome! If you've tested a new province, found a bug, or want to add a feature, open an issue or submit a PR.

## License

[AGPL-3.0](LICENSE) — free to use, modify, and distribute. Keep it open source.

## Acknowledgments

CitaYa is based on [`cita-bot`](https://github.com/cita-bot/cita-bot). It swaps Selenium for Playwright CDP over real Chrome, adds CapSolver captcha solving, supports more procedures, and restructures the project as a proper Python package.
