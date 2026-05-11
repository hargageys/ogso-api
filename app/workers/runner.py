"""APScheduler-based worker. Run as: python -m app.workers.runner"""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.workers.embedder import run_embedder
from app.workers.clusterer import run_clusterer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_embedder, "interval", hours=1, id="embedder")
    scheduler.add_job(run_clusterer, "interval", weeks=1, id="clusterer")
    scheduler.start()
    logger.info("Worker scheduler started (embedder: hourly, clusterer: weekly)")

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
