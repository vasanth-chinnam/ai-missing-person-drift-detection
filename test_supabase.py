import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from the .env file in the root directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def test_supabase():
    print(f"Connecting to: {SUPABASE_URL}")
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: Missing Supabase credentials in .env")
        return

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 1. Try to fetch the latest location
        print("Checking connection and fetching latest data...")
        response = supabase.table("locations").select("*").order("created_at", desc=True).limit(5).execute()
        
        if response.data:
            print(f"✅ Connection Successful! Found {len(response.data)} recent locations.")
            for i, row in enumerate(response.data):
                print(f"  [{i+1}] Lat: {row['latitude']}, Lon: {row['longitude']}, Time: {row['created_at']}")
        else:
            print("⚠️ Connection successful, but the 'locations' table is empty.")
            
    except Exception as e:
        print(f"❌ Supabase Connection Failed: {e}")

if __name__ == "__main__":
    test_supabase()
