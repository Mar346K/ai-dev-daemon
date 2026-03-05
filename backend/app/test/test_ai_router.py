from unittest.mock import patch, MagicMock
from app.core.ai_router import AIRouter

@patch("app.core.ai_router.ResourceOptimizer.is_system_idle")
@patch("app.core.ai_router.httpx.Client.post")
def test_architectural_review_idle(mock_post: MagicMock, mock_idle: MagicMock) -> None:
    """
    Verifies that the 70B model is triggered when the system is idle,
    and that the flush command (keep_alive: 0) is called immediately afterward.
    """
    # 1. Force the system to appear 'idle'
    mock_idle.return_value = True
    
    # 2. Mock the Ollama generation response
    mock_response_generate = MagicMock()
    mock_response_generate.json.return_value = {"response": "Looks structurally sound."}
    
    # 3. Mock the Ollama flush response
    mock_response_flush = MagicMock()
    mock_response_flush.json.return_value = {"response": ""}
    
    # Queue the two responses
    mock_post.side_effect = [mock_response_generate, mock_response_flush]
    
    router = AIRouter()
    review = router.architectural_review("+ print('test')")
    
    # Verify the AI returned our mocked text
    assert review == "Looks structurally sound."
    
    # Verify httpx.post was called exactly twice (generate, then flush)
    assert mock_post.call_count == 2
    
    # Extract the payload from the second call and verify the memory flush parameter
    flush_call_args = mock_post.call_args_list[1]
    assert flush_call_args[1]["json"]["keep_alive"] == 0
    assert flush_call_args[1]["json"]["model"] == "llama3.3:70b"

@patch("app.core.ai_router.ResourceOptimizer.is_system_idle")
def test_architectural_review_busy(mock_idle: MagicMock) -> None:
    """
    Verifies that the heavy model is safely skipped if the CPU is under load.
    """
    # Force the system to appear 'busy'
    mock_idle.return_value = False
    
    router = AIRouter()
    review = router.architectural_review("+ print('test')")
    
    # The method should gracefully return None without calling the model
    assert review is None