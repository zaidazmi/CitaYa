# CitaYa

Automated appointment booking for Spanish extranjeria (cita previa). Runs 24/7 until it snags your slot.

> **Not a developer?** Copy this entire repository link and paste it into [ChatGPT](https://chat.openai.com), [Claude](https://claude.ai), or any AI assistant and ask: *"How do I set this up on my computer to book an appointment?"* — it will walk you through every step.

Uses **real Chrome via CDP** (Chrome DevTools Protocol) + **Playwright** to bypass the ICP site's F5 Shape Security bot detection. Captchas are solved automatically via [CapSolver](https://www.capsolver.com/).

## How it works

1. Launches your actual Chrome browser with remote debugging
2. Playwright connects via CDP -- F5 WAF sees a genuine browser session
3. Navigates the ICP appointment flow, fills your personal info
4. Polls for available appointments (~30s between checks)
5. When a slot appears: selects office, fills contact info, solves captcha, confirms
6. Saves a screenshot of the confirmed booking

## Why real Chrome?

The ICP site runs F5 Shape Security (`TSPD_101`) which fingerprints the browser deeply -- TLS handshake, JS engine, canvas, WebGL. Headless browsers and patched Chromium builds get caught. Real Chrome via CDP passes because F5 sees an authentic browser session with matching fingerprints.

## Supported procedures

Procedure availability varies by province. The bot supports all procedures listed below.

### Police procedures (Tramites Policia Nacional)

| Code | Procedure |
|------|-----------|
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
| `ASILO_PRIMERA_CITA` | Asilo -- primera cita |
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

### Extranjeria procedures (Oficinas de Extranjeria)

These procedures are available in provinces with extranjeria offices (e.g. Alicante, Malaga, Zaragoza).

| Code | Procedure |
|------|-----------|
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

All Spanish provinces are supported. Procedures have been verified against the live ICP site for: **Barcelona, Madrid, Valencia, Malaga, Alicante, Sevilla, and Zaragoza**. Other provinces use the same system and should work, but procedure availability varies by province.

## Requirements

- Python 3.10+
- Google Chrome (the real browser, not Chromium)
- A [CapSolver](https://www.capsolver.com/) API key for automatic captcha solving

## Installation

```bash
git clone https://github.com/zaidazmi/CitaYa.git
cd CitaYa
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Quick start

1. Copy the example and fill in your details:

```bash
cp example.py my_appointment.py
```

2. Edit `my_appointment.py`:

```python
import logging
import sys

from citaya import CustomerProfile, DocType, OperationType, Province, run

logging.basicConfig(
    format="%(asctime)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

customer = CustomerProfile(
    capsolver_api_key="YOUR-CAPSOLVER-API-KEY",
    auto_captcha=True,
    auto_office=True,
    save_screenshots=True,
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

3. Run:

```bash
source .venv/bin/activate
python3 -u my_appointment.py
```

A Chrome window opens and the bot starts polling. Leave it running.

## Configuration

### Required fields

| Field | Description |
|-------|-------------|
| `name` | Full name (first and last) |
| `doc_type` | `DocType.NIE`, `DocType.PASSPORT`, or `DocType.DNI` |
| `doc_value` | Document number (no spaces) |
| `phone` | Phone number, e.g. `"600000000"` |
| `email` | Email address |
| `province` | `Province.BARCELONA`, `Province.MADRID`, etc. |
| `operation_code` | Procedure type (see table above) |
| `country` | Country name as shown on the ICP site (e.g. `"INDIA"`, `"MARRUECOS"`) |

### Optional fields

| Field | Default | Description |
|-------|---------|-------------|
| `capsolver_api_key` | `None` | CapSolver API key for auto captcha |
| `auto_captcha` | `True` | Solve captchas automatically |
| `auto_office` | `True` | Auto-select available office |
| `chrome_path` | auto-detect | Path to Chrome binary (auto-detected on macOS, Linux, Windows) |
| `headless` | `False` | Run Chrome in headless mode |
| `save_screenshots` | `False` | Save screenshots on events |
| `offices` | `[]` | Specific offices to try (list of `Office` enum values) |
| `except_offices` | `[]` | Offices to exclude |
| `min_date` | `None` | Skip dates before this (`"dd/mm/yyyy"`) |
| `max_date` | `None` | Skip dates after this (`"dd/mm/yyyy"`) |
| `year_of_birth` | `None` | Required for some procedures |
| `sms_webhook_token` | `None` | For auto SMS verification (see below) |
| `wait_exact_time` | `None` | `[[minute, second]]` -- submit at exact time |

## SMS auto-verification (optional)

Some appointments require SMS confirmation. To automate this:

1. Get a token from [webhook.site](https://webhook.site)
2. Set `sms_webhook_token` in your config
3. Use [IFTTT](https://ifttt.com/) on your phone: when SMS contains "CITA PREVIA", forward to your webhook.site email

## Troubleshooting

**Logs not appearing in real-time?**
Run with `python3 -u` (unbuffered output).

**WAF blocking?**
The bot auto-detects WAF blocks, restarts the browser with a fresh session, and backs off 3-4 minutes before retrying. No action needed.

**Rate limited (429)?**
Auto-detected -- the bot backs off 30-60 seconds.

**Port 9222 in use?**
Kill stale Chrome: `pkill -f "remote-debugging-port=9222"`

**Certificate errors in your normal browser?**
The bot uses a separate Chrome profile (`~/.chrome-citaya`). Your regular Chrome is unaffected.

**Chrome not found?**
The bot auto-detects Chrome on macOS, Linux, and Windows. If detection fails, set `chrome_path` in your `CustomerProfile`.

## License

[AGPL-3.0](LICENSE)
