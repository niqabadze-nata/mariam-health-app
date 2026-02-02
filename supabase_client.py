



import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()  # loads .env locally (Render ignores if not present)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Missing SUPABASE_URL or SUPABASE_KEY. "
        "Set them in Render -> Environment or in a local .env file."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
