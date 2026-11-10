import asyncio
import logging

logger = logging.getLogger(__name__)


class AutomationWorker:
    """Single-loop worker; database leases prevent duplicate claims across processes."""

    def __init__(self, store, agent, poll_seconds: int = 5, timeout_seconds: int = 120):
        self.store = store
        self.agent = agent
        self.poll_seconds = max(1, poll_seconds)
        self.timeout_seconds = max(10, timeout_seconds)
        self._stopping = asyncio.Event()

    async def run(self) -> None:
        self._stopping.clear()
        while not self._stopping.is_set():
            try:
                job = await asyncio.to_thread(lambda: self.store.claim_due(lease_seconds=self.timeout_seconds + 60))
                if job:
                    await self._execute(job)
                    continue
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Automation worker cycle failed")
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=self.poll_seconds)
            except asyncio.TimeoutError:
                pass

    async def stop(self) -> None:
        self._stopping.set()

    async def _execute(self, job: dict) -> None:
        execution_id = job["execution_id"]
        try:
            result = await asyncio.wait_for(
                self.agent.run(job["prompt"]),
                timeout=self.timeout_seconds,
            )
            await asyncio.to_thread(
                self.store.finish, job["id"], execution_id, result.get("answer", "")
            )
        except asyncio.CancelledError:
            await asyncio.to_thread(
                self.store.fail, job["id"], execution_id, "Worker shutdown interrupted execution"
            )
            raise
        except Exception as exc:
            logger.exception("Automation execution failed: %s", job["id"])
            await asyncio.to_thread(
                self.store.fail, job["id"], execution_id, f"{type(exc).__name__}: {exc}"
            )
