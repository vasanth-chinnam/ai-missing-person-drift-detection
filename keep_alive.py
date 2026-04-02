import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from the .env file in the root directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def ping_supabase():
    print(f"Connecting to: {SUPABASE_URL}")
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: Missing Supabase credentials in .env")
        return

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Perform a simple select to trigger activity
        print("Pinging Supabase to maintain activity...")
        response = supabase.table("locations").select("id").limit(1).execute()
        
        print("✅ Ping Successful!")
            
    except Exception as e:
        print(f"❌ Ping Failed: {e}")

if __name__ == "__main__":
    # You can run this once or in a loop
    # To run once:
    ping_supabase()
    
    # To run every 6 days (Supabase pauses after 7 days of inactivity):
    # while True:
    #     ping_supabase()
    #     time.sleep(6 * 24 * 60 * 60)
