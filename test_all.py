#!/usr/bin/env python3
import asyncio
import aiohttp
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, List
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = os.getenv("BASE_URL", "https://finaltry-4-production.up.railway.app")
TEST_EMAIL = os.getenv("TEST_EMAIL", "test@example.com")

class ComponentTester:
    def __init__(self):
        self.results: Dict[str, bool] = {}
        self.session = None

    async def setup(self):
        self.session = aiohttp.ClientSession()

    async def cleanup(self):
        if self.session:
            await self.session.close()

    async def test_health_endpoints(self) -> bool:
        """Test health and readiness endpoints."""
        try:
            # Test /health
            async with self.session.get(f"{BASE_URL}/health") as response:
                if response.status != 200:
                    logger.error(f"Health check failed: {response.status}")
                    return False
                data = await response.json()
                logger.info(f"Health check response: {data}")

            # Test /ready
            async with self.session.get(f"{BASE_URL}/ready") as response:
                if response.status != 200:
                    logger.error(f"Readiness check failed: {response.status}")
                    return False
                data = await response.json()
                logger.info(f"Readiness check response: {data}")

            return True
        except Exception as e:
            logger.error(f"Health endpoints test failed: {e}")
            return False

    async def test_metrics(self) -> bool:
        """Test metrics endpoint."""
        try:
            async with self.session.get(f"{BASE_URL}/metrics") as response:
                if response.status != 200:
                    logger.error(f"Metrics check failed: {response.status}")
                    return False
                data = await response.json()
                logger.info(f"Metrics response: {data}")
                return True
        except Exception as e:
            logger.error(f"Metrics test failed: {e}")
            return False

    async def test_supabase(self) -> bool:
        """Test Supabase integration."""
        try:
            # Test leads endpoint
            async with self.session.get(f"{BASE_URL}/api/v1/leads") as response:
                if response.status != 200:
                    logger.error(f"Leads endpoint failed: {response.status}")
                    return False
                data = await response.json()
                logger.info(f"Leads response: {data}")

            # Test follow-ups
            async with self.session.get(f"{BASE_URL}/api/v1/followups") as response:
                if response.status != 200:
                    logger.error(f"Follow-ups endpoint failed: {response.status}")
                    return False
                data = await response.json()
                logger.info(f"Follow-ups response: {data}")

            return True
        except Exception as e:
            logger.error(f"Supabase test failed: {e}")
            return False

    async def test_email_service(self) -> bool:
        """Test email service."""
        try:
            payload = {
                "to": TEST_EMAIL,
                "subject": f"Test Email - {datetime.utcnow().isoformat()}",
                "body": "This is a test email from the comprehensive test script."
            }

            async with self.session.post(f"{BASE_URL}/api/v1/email/send", json=payload) as response:
                if response.status != 200:
                    logger.error(f"Email send failed: {response.status}")
                    return False
                data = await response.json()
                logger.info(f"Email send response: {data}")
                return True
        except Exception as e:
            logger.error(f"Email service test failed: {e}")
            return False

    async def test_scheduler(self) -> bool:
        """Test scheduler functionality."""
        try:
            # Check scheduler status in metrics
            async with self.session.get(f"{BASE_URL}/metrics") as response:
                if response.status != 200:
                    return False
                data = await response.json()
                if "scheduler" not in data.get("services", {}):
                    logger.error("Scheduler metrics not found")
                    return False
                logger.info(f"Scheduler metrics: {data['services']['scheduler']}")
                return True
        except Exception as e:
            logger.error(f"Scheduler test failed: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """Run all component tests."""
        try:
            await self.setup()
            
            tests = [
                ("Health Endpoints", self.test_health_endpoints),
                ("Metrics", self.test_metrics),
                ("Supabase", self.test_supabase),
                ("Email Service", self.test_email_service),
                ("Scheduler", self.test_scheduler)
            ]

            for name, test in tests:
                logger.info(f"\nRunning {name} test...")
                try:
                    result = await test()
                    self.results[name] = result
                    logger.info(f"{name}: {'✅ PASS' if result else '❌ FAIL'}")
                except Exception as e:
                    logger.error(f"{name} test error: {e}")
                    self.results[name] = False

            # Print summary
            logger.info("\nTest Summary:")
            logger.info("=" * 50)
            for name, result in self.results.items():
                logger.info(f"{name}: {'✅ PASS' if result else '❌ FAIL'}")
            logger.info("=" * 50)

            return all(self.results.values())
        finally:
            await self.cleanup()

async def main():
    tester = ComponentTester()
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 