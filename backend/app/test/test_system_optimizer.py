from app.core.system_optimizer import ResourceOptimizer
import psutil
import os

def test_isolate_daemon_process() -> None:
    """
    Verifies that the daemon successfully restricts its own CPU affinity and priority.
    """
    status = ResourceOptimizer.isolate_daemon_process()
    
    assert status["priority_set"] is True
    
    # We only assert affinity if the machine has enough cores
    logical_cores = psutil.cpu_count(logical=True)
    if logical_cores and logical_cores >= 4:
        assert status["affinity_set"] is True
        assert len(status["cores_assigned"]) == 2
        
        # Verify the OS actually applied the affinity
        process = psutil.Process(os.getpid())
        assert process.cpu_affinity() == status["cores_assigned"]

def test_system_idle_check() -> None:
    """
    Verifies the CPU threshold checker returns a valid boolean.
    """
    is_idle = ResourceOptimizer.is_system_idle(cpu_threshold=100.0) 
    assert is_idle is True # 100% threshold should always return True