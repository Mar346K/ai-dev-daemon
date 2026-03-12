import os
import psutil
from fastapi import HTTPException
from app.core.telemetry import daemon_logger

# Professional Standard: Set a strict threshold for hardware saturation
CRITICAL_MEMORY_THRESHOLD = 90.0

def check_hardware_capacity() -> None:
    """
    Acts as a circuit breaker. Checks current system memory pressure.
    If the system is saturated, raises a 503 to gracefully degrade rather than crash.
    """
    mem = psutil.virtual_memory()
    
    if mem.percent >= CRITICAL_MEMORY_THRESHOLD:
        daemon_logger.warning(
            f"Hardware fencing triggered. System RAM at {mem.percent}%. "
            "Rejecting AI request to prevent system crash."
        )
        raise HTTPException(
            status_code=503,
            detail=f"Hardware Fencing: System memory is critically saturated ({mem.percent}%). "
                   "AI operations temporarily suspended to protect system stability."
        )

class ResourceOptimizer:
    """
    Manages OS-level process priority and CPU affinity to ensure the AI daemon
    runs silently in the background without degrading main system performance.
    """
    @staticmethod
    def isolate_daemon_process() -> dict[str, any]:
        """
        Demotes the current process priority to 'Below Normal' and restricts
        CPU execution to the final two logical cores.
        """
        process = psutil.Process(os.getpid())
        status = {"priority_set": False, "affinity_set": False, "cores_assigned": []}

        try:
            # Professional Standard: Windows-specific priority demotion
            process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            status["priority_set"] = True
        except (psutil.AccessDenied, AttributeError):
            pass # Failsafe if running in a restricted permission context

        try:
            # Dynamically grab the total thread count and bind to the last two
            logical_cores = psutil.cpu_count(logical=True)
            if logical_cores and logical_cores >= 4:
                target_cores = [logical_cores - 2, logical_cores - 1]
                process.cpu_affinity(target_cores)
                status["affinity_set"] = True
                status["cores_assigned"] = target_cores
        except (psutil.AccessDenied, AttributeError, ValueError):
            pass

        return status

    @staticmethod
    def is_system_idle(cpu_threshold: float = 15.0) -> bool:
        """
        Checks if the overall system CPU usage is below the threshold,
        acting as a gatekeeper before triggering the heavy 70B architectural model.
        """
        # A 1-second interval ensures an accurate reading, not an instantaneous spike
        current_load = psutil.cpu_percent(interval=1.0)
        return current_load < cpu_threshold