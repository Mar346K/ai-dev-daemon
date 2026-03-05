import os
import psutil

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