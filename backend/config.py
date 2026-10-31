import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

TENDER_SOURCE = "OpenCity BBMP Tenders 2017-18"
TENDER_SOURCE_URL = "https://data.opencity.in/dataset/bbmp-tenders"
WO_SOURCE = "OpenCity BBMP Work Orders and Payments 2025-26 (198 wards)"
WO_SOURCE_URL = "https://data.opencity.in/dataset/bbmp-work-orders-and-payments-2025-26"
GRIEV_SOURCE = "OpenCity BBMP Grievances 2024"
GRIEV_SOURCE_URL = "https://data.opencity.in/dataset/bbmp-grievances-data"
WARD_SOURCE = "OpenCity BBMP Ward Information"
WARD_SOURCE_URL = "https://data.opencity.in/dataset/bbmp-ward-information"
