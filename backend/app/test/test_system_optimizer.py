from app.core.system_optimizer import ResourceOptimizer
import psutil
import os
import pytest
from fastapi import HTTPException

def test_hardware_fencing_graceful_degradation(monkeypatch):
    """Verify that the system optimizer blocks execution if RAM pressure is critically high."""
    from app.core.system_optimizer import check_hardware_capacity
    import psutil
    from collections import namedtuple
    
    # Create a mock namedtuple to simulate psutil's virtual_memory output
    MockMem = namedtuple('vmem', ['percent'])
    
    # Scenario 1: Healthy system (50% RAM usage)
    def mock_healthy_mem():
        return MockMem(percent=50.0)
    monkeypatch.setattr(psutil, "virtual_memory", mock_healthy_mem)
    
    # Should pass silently without raising an error
    check_hardware_capacity()
    
    # Scenario 2: Overloaded system (95% RAM usage)
    def mock_overloaded_mem():
        return MockMem(percent=95.0)
    monkeypatch.setattr(psutil, "virtual_memory", mock_overloaded_mem)
    
    # Should throw a 503 Service Unavailable
    with pytest.raises(HTTPException) as exc_info:
        check_hardware_capacity()
        
    assert exc_info.value.status_code == 503
    assert "Hardware Fencing" in exc_info.value.detail
    
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