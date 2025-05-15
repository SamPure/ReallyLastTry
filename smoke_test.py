#!/usr/bin/env python3
import asyncio
import aiohttp
import logging
import sys
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "https://finaltry-4-production.up.railway.app"
TEST_EMAIL = "test@example.com"  # Replace with your test email

async def check_health() -> bool:
    """Check /health endpoint."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health") as response:
                if response.status != 200:
                    logger.error(f"Health check failed: {response.status}")
                    return False

                data = await response.json()
                logger.info(f"Health check response: {data}")

                if data["status"] != "healthy":
                    logger.error("Health check returned unhealthy status")
                    return False

                return True
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return False

async def check_readiness() -> bool:
    """Check /ready endpoint."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/ready") as response:
                if response.status != 200:
                    logger.error(f"Readiness check failed: {response.status}")
                    return False

                data = await response.json()
                logger.info(f"Readiness check response: {data}")

                if data["status"] != "ready":
                    logger.error("Readiness check returned not ready status")
                    return False

                return True
    except Exception as e:
        logger.error(f"Readiness check error: {e}")
        return False

async def send_test_email() -> bool:
    """Send a test email."""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "to": TEST_EMAIL,
                "subject": f"Smoke Test Email - {datetime.utcnow().isoformat()}",
                "body": "This is a test email from the smoke test script."
            }

            async with session.post(f"{BASE_URL}/api/v1/email/send", json=payload) as response:
                if response.status != 200:
                    logger.error(f"Test email failed: {response.status}")
                    return False

                data = await response.json()
                logger.info(f"Test email response: {data}")
                return True
    except Exception as e:
        logger.error(f"Test email error: {e}")
        return False

async def verify_supabase() -> bool:
    """Verify Supabase connectivity."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/v1/leads") as response:
                if response.status != 200:
                    logger.error(f"Supabase check failed: {response.status}")
                    return False

                data = await response.json()
                logger.info(f"Supabase check response: {data}")
                return True
    except Exception as e:
        logger.error(f"Supabase check error: {e}")
        return False

async def run_smoke_test() -> bool:
    """Run all smoke tests."""
    logger.info("Starting smoke test...")

    tests = [
        ("Health Check", check_health),
        ("Readiness Check", check_readiness),
        ("Supabase Check", verify_supabase),
        ("Test Email", send_test_email)
    ]

    results: Dict[str, bool] = {}

    for name, test in tests:
        logger.info(f"Running {name}...")
        try:
            result = await test()
            results[name] = result
            logger.info(f"{name}: {'✅ PASS' if result else '❌ FAIL'}")
        except Exception as e:
            logger.error(f"{name} error: {e}")
            results[name] = False

    # Print summary
    logger.info("\nSmoke Test Summary:")
    logger.info("=" * 50)
    for name, result in results.items():
        logger.info(f"{name}: {'✅ PASS' if result else '❌ FAIL'}")
    logger.info("=" * 50)

    return all(results.values())

if __name__ == "__main__":
    try:
        success = asyncio.run(run_smoke_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Smoke test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Smoke test failed: {e}")
        sys.exit(1)
