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
    province=Province.BARCELONA,
    operation_code=OperationType.TOMA_HUELLAS,  # Change to your procedure
    doc_type=DocType.NIE,                       # DocType.NIE, DocType.PASSPORT, or DocType.DNI
    doc_value="Y1234567X",                      # Your document number
    country="INDIA",                            # Your country (as shown on the ICP site)
    name="Your Name",                           # First and last name
    phone="600000000",                          # Phone number
    email="you@example.com",                    # Email
)


if __name__ == "__main__":
    run(context=customer, max_attempts=200)
