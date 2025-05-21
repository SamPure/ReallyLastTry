import asyncio
import aiohttp
import logging
import sys
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base URL for the application
BASE_URL = os.getenv('BASE_URL', 'https://finaltry-4-production.up.railway.app')

async def trigger_followups():
    """Trigger follow-ups and monitor their progress."""
    async with aiohttp.ClientSession() as session:
        try:
            # First check if the service is healthy
            async with session.get(f"{BASE_URL}/ready") as response:
                if response.status != 200:
                    logger.error("Service is not healthy")
                    return False
                logger.info("Service is healthy")

            # Trigger follow-ups
            logger.info("Triggering follow-ups...")
            async with session.post(f"{BASE_URL}/messaging/followups/trigger") as response:
                if response.status != 200:
                    logger.error(f"Failed to trigger follow-ups: {response.status}")
                    return False
                result = await response.json()
                logger.info(f"Follow-ups triggered: {result}")

            # Wait a bit for processing to start
            await asyncio.sleep(5)

            # Monitor metrics for follow-up processing
            async with session.get(f"{BASE_URL}/metrics") as response:
                if response.status == 200:
                    metrics = await response.text()
                    logger.info("Current metrics:")
                    logger.info(metrics)
                else:
                    logger.error("Failed to get metrics")

            return True

        except Exception as e:
            logger.error(f"Error during follow-up process: {str(e)}")
            return False

async def main():
    """Main function to run the follow-up test."""
    logger.info("Starting follow-up test...")
    
    success = await trigger_followups()
    
    if success:
        logger.info("Follow-up test completed successfully")
        sys.exit(0)
    else:
        logger.error("Follow-up test failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 