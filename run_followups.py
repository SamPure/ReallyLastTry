import asyncio
import os
import sys
from app.jobs.scheduler_service import run_followups
from app.services.config_manager import Settings

async def main():
    try:
        # Load settings
        settings = Settings()
        
        # Print environment info
        print(f"Environment: {settings.ENV}")
        print(f"Debug mode: {settings.DEBUG}")
        print(f"Supabase URL: {settings.SUPABASE_URL}")
        
        # Run follow-ups
        print("Starting follow-up process...")
        await run_followups()
        print("Follow-ups completed successfully")
        
    except Exception as e:
        print(f"Error running follow-ups: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 