import logging
import sys

from citaya import CustomerProfile, DocType, OperationType, Province, run

# Force real-time log output
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
    headless=False,                             # True to run without visible browser
    chrome_path=None,                           # Auto-detects Chrome, or set path manually
    province=Province.BARCELONA,
    operation_code=OperationType.TOMA_HUELLAS,  # Change to your procedure
    doc_type=DocType.NIE,                       # DocType.NIE, DocType.PASSPORT, or DocType.DNI
    doc_value="Y1234567X",                      # Your document number
    country="INDIA",                            # Your country (as shown on the ICP site)
    name="Your Name",                           # First and last name
    phone="600000000",                          # Phone number
    email="you@example.com",                    # Email
    year_of_birth=None,                         # Required for some procedures
    offices=[],                                 # Specific offices to try, or [] for any
    except_offices=[],                          # Offices to exclude
    min_date=None,                              # Skip dates before this ("dd/mm/yyyy")
    max_date=None,                              # Skip dates after this ("dd/mm/yyyy")
    min_time=None,                              # Skip times before this ("HH:MM")
    max_time=None,                              # Skip times after this ("HH:MM")
    sms_webhook_token=None,                     # For auto SMS verification (see README)
    wait_exact_time=None,                       # [[minute, second]] — submit at exact time
)


if __name__ == "__main__":
    run(context=customer, max_attempts=200)
