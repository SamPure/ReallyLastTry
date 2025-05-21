#!/usr/bin/env python3
import asyncio
import aiohttp
import logging
import sys
import os
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = os.getenv("BASE_URL", "https://finaltry-4-production.up.railway.app")

async def trigger_followups():
    """Trigger the follow-up process manually."""
    try:
        async with aiohttp.ClientSession() as session:
            # First check if scheduler is healthy
            async with session.get(f"{BASE_URL}/ready") as response:
                if response.status != 200:
                    logger.error(f"Scheduler not ready: {response.status}")
                    return False
                data = await response.json()
                logger.info(f"Scheduler status: {data}")

            # Trigger follow-ups
            async with session.post(f"{BASE_URL}/api/v1/followups/trigger") as response:
                if response.status != 200:
                    logger.error(f"Failed to trigger follow-ups: {response.status}")
                    return False
                data = await response.json()
                logger.info(f"Follow-up trigger response: {data}")

            # Wait a bit for processing
            await asyncio.sleep(5)

            # Check metrics to verify follow-ups were processed
            async with session.get(f"{BASE_URL}/metrics") as response:
                if response.status != 200:
                    logger.error(f"Failed to get metrics: {response.status}")
                    return False
                data = await response.json()
                logger.info(f"Follow-up metrics: {data.get('services', {}).get('followup', {})}")

            return True
    except Exception as e:
        logger.error(f"Error triggering follow-ups: {e}")
        return False

async def monitor_followups():
    """Monitor follow-up processing for 5 minutes."""
    try:
        async with aiohttp.ClientSession() as session:
            start_time = datetime.utcnow()
            while (datetime.utcnow() - start_time).total_seconds() < 300:  # 5 minutes
                async with session.get(f"{BASE_URL}/metrics") as response:
                    if response.status == 200:
                        data = await response.json()
                        followup_metrics = data.get('services', {}).get('followup', {})
                        logger.info(f"Current follow-up metrics: {followup_metrics}")
                await asyncio.sleep(30)  # Check every 30 seconds
    except Exception as e:
        logger.error(f"Error monitoring follow-ups: {e}")

async def main():
    try:
        logger.info("Starting follow-up test...")
        
        # Trigger follow-ups
        success = await trigger_followups()
        if not success:
            logger.error("Failed to trigger follow-ups")
            sys.exit(1)
            
        # Monitor processing
        logger.info("Monitoring follow-up processing for 5 minutes...")
        await monitor_followups()
        
        logger.info("Follow-up test completed")
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 