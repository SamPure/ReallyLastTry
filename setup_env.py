import os
import sys
import asyncio
from app.jobs.scheduler_service import run_followups
from app.services.config_manager import Settings

# Set environment variables - Replace these with your actual values
# You can set these in your deployment environment or use a .env file
os.environ["SUPABASE_URL"] = "YOUR_SUPABASE_URL"
os.environ["SUPABASE_SERVICE_KEY"] = "YOUR_SUPABASE_SERVICE_KEY"
os.environ["EMAIL_SENDER"] = "YOUR_EMAIL"
os.environ["EMAIL_PASSWORD"] = "YOUR_EMAIL_PASSWORD"
os.environ["SMTP_SERVER"] = "smtp.gmail.com"
os.environ["SMTP_PORT"] = "587"
os.environ["GMAIL_USER"] = "YOUR_GMAIL"
os.environ["GMAIL_APP_PASSWORD"] = "YOUR_GMAIL_APP_PASSWORD"
os.environ["GMAIL_CLIENT_ID"] = "YOUR_GMAIL_CLIENT_ID"
os.environ["GMAIL_CLIENT_SECRET"] = "YOUR_GMAIL_CLIENT_SECRET"
os.environ["GMAIL_REFRESH_TOKEN"] = "YOUR_GMAIL_REFRESH_TOKEN"
os.environ["SHEET_ID"] = "YOUR_SHEET_ID"
os.environ["SHEET_NAME"] = "AllLeads"
os.environ["SHEET_API_KEY"] = "YOUR_SHEET_API_KEY"
os.environ["KIXIE_BASE_URL"] = "https://api.kixie.com/v1"
os.environ["KIXIE_API_KEY"] = "YOUR_KIXIE_API_KEY"
os.environ["KIXIE_BUSINESS_ID"] = "YOUR_KIXIE_BUSINESS_ID"
os.environ["ENABLE_GOOGLE_SHEETS_SYNC"] = "true"
os.environ["ENABLE_EMAIL_FALLBACK"] = "true"
os.environ["ENABLE_DAILY_REPORTS"] = "true"
os.environ["BUSINESS_HOURS_START"] = "9"
os.environ["BUSINESS_HOURS_END"] = "17"
os.environ["REPORT_EMAIL"] = "YOUR_REPORT_EMAIL"
os.environ["REPORT_TIMEZONE"] = "America/New_York"
os.environ["LOG_LEVEL"] = "info"

async def main():
    # Load settings
    settings = Settings()
    
    # Print environment info
    print(f"Environment: {settings.ENV}")
    print(f"Debug mode: {settings.DEBUG}")
    print(f"Supabase URL: {settings.SUPABASE_URL}")
    
    try:
        # Run follow-ups
        print("Starting follow-up process...")
        await run_followups()
        print("Follow-ups completed successfully")
    except Exception as e:
        print(f"Error running follow-ups: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 