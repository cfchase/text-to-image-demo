"""Tests for background tasks."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from api.background import (
    BackgroundTaskManager,
    CleanupTask,
    HealthCheckTask,
)
from storage.base import AbstractStorage


class TestCleanupTask:
    """Test CleanupTask functionality."""
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage for testing."""
        storage = AsyncMock(spec=AbstractStorage)
        storage.cleanup_expired_images.return_value = 5
        return storage
    
    @pytest.fixture
    def cleanup_task(self, mock_storage):
        """Create cleanup task for testing."""
        return CleanupTask(
            storage=mock_storage,
            interval=1,  # 1 second for testing
            ttl=3600,    # 1 hour TTL
        )
    
    def test_initialization(self, cleanup_task, mock_storage):
        """Test CleanupTask initialization."""
        assert cleanup_task.storage == mock_storage
        assert cleanup_task.interval == 1
        assert cleanup_task.ttl == 3600
        assert cleanup_task.running is False
        assert cleanup_task.task is None
    
    @pytest.mark.asyncio
    async def test_start_stop(self, cleanup_task):
        """Test starting and stopping cleanup task."""
        # Start task
        await cleanup_task.start()
        
        assert cleanup_task.running is True
        assert cleanup_task.task is not None
        assert not cleanup_task.task.done()
        
        # Stop task
        await cleanup_task.stop()
        
        assert cleanup_task.running is False
        assert cleanup_task.task is None
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, cleanup_task):
        """Test starting task when already running."""
        await cleanup_task.start()
        original_task = cleanup_task.task
        
        # Try to start again
        await cleanup_task.start()
        
        # Should be the same task
        assert cleanup_task.task == original_task
        
        await cleanup_task.stop()
    
    @pytest.mark.asyncio
    async def test_stop_not_running(self, cleanup_task):
        """Test stopping task when not running."""
        # Should not raise exception
        await cleanup_task.stop()
        
        assert cleanup_task.running is False
        assert cleanup_task.task is None
    
    @pytest.mark.asyncio
    async def test_run_cleanup_success(self, cleanup_task, mock_storage):
        """Test successful cleanup run."""
        mock_storage.cleanup_expired_images.return_value = 3
        
        deleted_count = await cleanup_task.run_cleanup()
        
        assert deleted_count == 3
        mock_storage.cleanup_expired_images.assert_called_once_with(3600)
    
    @pytest.mark.asyncio
    async def test_run_cleanup_no_images(self, cleanup_task, mock_storage):
        """Test cleanup run with no images to delete."""
        mock_storage.cleanup_expired_images.return_value = 0
        
        deleted_count = await cleanup_task.run_cleanup()
        
        assert deleted_count == 0
    
    @pytest.mark.asyncio
    async def test_run_cleanup_storage_error(self, cleanup_task, mock_storage):
        """Test cleanup run with storage error."""
        mock_storage.cleanup_expired_images.side_effect = Exception("Storage error")
        
        with pytest.raises(Exception, match="Storage error"):
            await cleanup_task.run_cleanup()
    
    @pytest.mark.asyncio
    async def test_cleanup_loop_runs_multiple_times(self, mock_storage):
        """Test that cleanup loop runs multiple times."""
        mock_storage.cleanup_expired_images.return_value = 1
        
        # Very short interval for testing
        cleanup_task = CleanupTask(
            storage=mock_storage,
            interval=0.1,  # 100ms
            ttl=3600,
        )
        
        await cleanup_task.start()
        
        # Wait for multiple cleanup cycles
        await asyncio.sleep(0.5)
        
        await cleanup_task.stop()
        
        # Should have been called multiple times
        assert mock_storage.cleanup_expired_images.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_cleanup_loop_handles_errors(self, mock_storage):
        """Test that cleanup loop handles errors gracefully."""
        # First call fails, subsequent calls succeed
        mock_storage.cleanup_expired_images.side_effect = [
            Exception("First failure"),
            2,  # Success
            Exception("Second failure"),
            1,  # Success
        ]
        
        cleanup_task = CleanupTask(
            storage=mock_storage,
            interval=0.1,
            ttl=3600,
        )
        
        await cleanup_task.start()
        
        # Wait for multiple cycles (including error recovery)
        await asyncio.sleep(0.5)
        
        await cleanup_task.stop()
        
        # Should have continued running despite errors
        assert mock_storage.cleanup_expired_images.call_count >= 3
    
    def test_is_running(self, cleanup_task):
        """Test is_running method."""
        assert cleanup_task.is_running() is False
        
        # Mock running state
        cleanup_task.running = True
        cleanup_task.task = MagicMock()
        cleanup_task.task.done.return_value = False
        
        assert cleanup_task.is_running() is True
        
        # Mock completed task
        cleanup_task.task.done.return_value = True
        assert cleanup_task.is_running() is False
    
    def test_get_status(self, cleanup_task):
        """Test get_status method."""
        status = cleanup_task.get_status()
        
        assert status["running"] is False
        assert status["interval"] == 1
        assert status["ttl"] == 3600
        assert status["task_active"] is False


class TestHealthCheckTask:
    """Test HealthCheckTask functionality."""
    
    @pytest.fixture
    def mock_health_check_func(self):
        """Mock health check function."""
        func = AsyncMock()
        func.return_value = {"service": "healthy", "timestamp": "2024-01-01T12:00:00Z"}
        return func
    
    @pytest.fixture
    def health_check_task(self, mock_health_check_func):
        """Create health check task for testing."""
        return HealthCheckTask(
            health_check_func=mock_health_check_func,
            interval=1,  # 1 second for testing
            failure_threshold=2,
        )
    
    def test_initialization(self, health_check_task, mock_health_check_func):
        """Test HealthCheckTask initialization."""
        assert health_check_task.health_check_func == mock_health_check_func
        assert health_check_task.interval == 1
        assert health_check_task.failure_threshold == 2
        assert health_check_task.running is False
        assert health_check_task.task is None
        assert health_check_task.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self, health_check_task):
        """Test starting and stopping health check task."""
        await health_check_task.start()
        
        assert health_check_task.running is True
        assert health_check_task.task is not None
        
        await health_check_task.stop()
        
        assert health_check_task.running is False
        assert health_check_task.task is None
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, health_check_task, mock_health_check_func):
        """Test successful health check."""
        mock_health_check_func.return_value = {"service": "healthy"}
        
        await health_check_task._run_health_check()
        
        assert health_check_task.consecutive_failures == 0
        assert health_check_task.last_status["service"] == "healthy"
        mock_health_check_func.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, health_check_task, mock_health_check_func):
        """Test health check failure."""
        mock_health_check_func.return_value = {"service": "unhealthy"}
        
        await health_check_task._run_health_check()
        
        assert health_check_task.consecutive_failures == 1
        assert health_check_task.last_status["service"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_exception(self, health_check_task, mock_health_check_func):
        """Test health check with exception."""
        mock_health_check_func.side_effect = Exception("Health check failed")
        
        await health_check_task._run_health_check()
        
        assert health_check_task.consecutive_failures == 1
        assert health_check_task.last_status["service"] == "unhealthy"
        assert "Health check failed" in health_check_task.last_status["error"]
    
    @pytest.mark.asyncio
    async def test_failure_threshold_tracking(self, health_check_task, mock_health_check_func):
        """Test failure threshold tracking."""
        mock_health_check_func.return_value = {"service": "unhealthy"}
        
        # First failure (below threshold)
        await health_check_task._run_health_check()
        assert health_check_task.consecutive_failures == 1
        
        # Second failure (at threshold)
        await health_check_task._run_health_check()
        assert health_check_task.consecutive_failures == 2
        
        # Third failure (above threshold)
        await health_check_task._run_health_check()
        assert health_check_task.consecutive_failures == 3
    
    @pytest.mark.asyncio
    async def test_recovery_resets_failures(self, health_check_task, mock_health_check_func):
        """Test that recovery resets failure count."""
        # Simulate failures
        mock_health_check_func.return_value = {"service": "unhealthy"}
        await health_check_task._run_health_check()
        await health_check_task._run_health_check()
        assert health_check_task.consecutive_failures == 2
        
        # Simulate recovery
        mock_health_check_func.return_value = {"service": "healthy"}
        await health_check_task._run_health_check()
        assert health_check_task.consecutive_failures == 0
    
    def test_get_status(self, health_check_task):
        """Test get_status method."""
        # Set some test data
        health_check_task.consecutive_failures = 1
        health_check_task.last_check_time = datetime.now(timezone.utc)
        health_check_task.last_status = {"service": "unhealthy"}
        
        status = health_check_task.get_status()
        
        assert status["running"] is False
        assert status["interval"] == 1
        assert status["failure_threshold"] == 2
        assert status["consecutive_failures"] == 1
        assert status["last_check_time"] is not None
        assert status["last_status"]["service"] == "unhealthy"


class TestBackgroundTaskManager:
    """Test BackgroundTaskManager functionality."""
    
    @pytest.fixture
    def task_manager(self):
        """Create background task manager for testing."""
        return BackgroundTaskManager()
    
    @pytest.fixture
    def mock_task(self):
        """Mock background task."""
        task = MagicMock()
        task.start = AsyncMock()
        task.stop = AsyncMock()
        task.get_status = MagicMock(return_value={"running": True})
        return task
    
    def test_initialization(self, task_manager):
        """Test BackgroundTaskManager initialization."""
        assert task_manager.tasks == {}
        assert task_manager.running is False
    
    def test_add_task(self, task_manager, mock_task):
        """Test adding a task."""
        task_manager.add_task("test_task", mock_task)
        
        assert "test_task" in task_manager.tasks
        assert task_manager.tasks["test_task"] == mock_task
    
    def test_add_task_replace_existing(self, task_manager, mock_task):
        """Test replacing an existing task."""
        task_manager.add_task("test_task", mock_task)
        
        new_task = MagicMock()
        task_manager.add_task("test_task", new_task)
        
        assert task_manager.tasks["test_task"] == new_task
    
    @pytest.mark.asyncio
    async def test_start_all_tasks(self, task_manager, mock_task):
        """Test starting all tasks."""
        task_manager.add_task("task1", mock_task)
        
        second_task = MagicMock()
        second_task.start = AsyncMock()
        task_manager.add_task("task2", second_task)
        
        await task_manager.start_all()
        
        assert task_manager.running is True
        mock_task.start.assert_called_once()
        second_task.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_all_already_running(self, task_manager, mock_task):
        """Test starting all tasks when already running."""
        task_manager.add_task("test_task", mock_task)
        task_manager.running = True
        
        await task_manager.start_all()
        
        # Should not call start on tasks
        mock_task.start.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_start_all_with_failure(self, task_manager):
        """Test starting all tasks with one task failing."""
        failing_task = MagicMock()
        failing_task.start = AsyncMock(side_effect=Exception("Start failed"))
        
        success_task = MagicMock()
        success_task.start = AsyncMock()
        
        task_manager.add_task("failing_task", failing_task)
        task_manager.add_task("success_task", success_task)
        
        # Should not raise exception
        await task_manager.start_all()
        
        assert task_manager.running is True
        failing_task.start.assert_called_once()
        success_task.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_all_tasks(self, task_manager, mock_task):
        """Test stopping all tasks."""
        task_manager.add_task("task1", mock_task)
        
        second_task = MagicMock()
        second_task.stop = AsyncMock()
        task_manager.add_task("task2", second_task)
        
        task_manager.running = True
        
        await task_manager.stop_all()
        
        assert task_manager.running is False
        mock_task.stop.assert_called_once()
        second_task.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_all_not_running(self, task_manager, mock_task):
        """Test stopping all tasks when not running."""
        task_manager.add_task("test_task", mock_task)
        
        await task_manager.stop_all()
        
        # Should not call stop on tasks
        mock_task.stop.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_stop_all_with_failure(self, task_manager):
        """Test stopping all tasks with one task failing."""
        failing_task = MagicMock()
        failing_task.stop = AsyncMock(side_effect=Exception("Stop failed"))
        
        success_task = MagicMock()
        success_task.stop = AsyncMock()
        
        task_manager.add_task("failing_task", failing_task)
        task_manager.add_task("success_task", success_task)
        task_manager.running = True
        
        # Should not raise exception
        await task_manager.stop_all()
        
        assert task_manager.running is False
        failing_task.stop.assert_called_once()
        success_task.stop.assert_called_once()
    
    def test_get_status(self, task_manager, mock_task):
        """Test get_status method."""
        task_manager.add_task("test_task", mock_task)
        task_manager.running = True
        
        status = task_manager.get_status()
        
        assert status["manager_running"] is True
        assert status["task_count"] == 1
        assert "test_task" in status["tasks"]
        assert status["tasks"]["test_task"]["running"] is True
    
    def test_get_status_task_without_get_status_method(self, task_manager):
        """Test get_status with task that doesn't have get_status method."""
        simple_task = MagicMock()
        simple_task.running = True
        del simple_task.get_status  # Remove get_status method
        
        task_manager.add_task("simple_task", simple_task)
        
        status = task_manager.get_status()
        
        assert "simple_task" in status["tasks"]
        assert status["tasks"]["simple_task"]["running"] is True
        assert status["tasks"]["simple_task"]["type"] == "MagicMock"
    
    def test_get_status_task_with_error(self, task_manager):
        """Test get_status with task that raises error."""
        error_task = MagicMock()
        error_task.get_status.side_effect = Exception("Status error")
        
        task_manager.add_task("error_task", error_task)
        
        status = task_manager.get_status()
        
        assert "error_task" in status["tasks"]
        assert "error" in status["tasks"]["error_task"]
        assert "Status error" in status["tasks"]["error_task"]["error"]


@pytest.mark.integration
class TestBackgroundTaskIntegration:
    """Integration tests for background tasks."""
    
    @pytest.mark.asyncio
    async def test_cleanup_and_health_check_together(self, mock_storage):
        """Test running cleanup and health check tasks together."""
        mock_storage.cleanup_expired_images.return_value = 2
        
        # Create health check function
        async def mock_health_check():
            return {"service": "healthy"}
        
        # Create tasks
        cleanup_task = CleanupTask(
            storage=mock_storage,
            interval=0.1,
            ttl=3600,
        )
        
        health_check_task = HealthCheckTask(
            health_check_func=mock_health_check,
            interval=0.1,
            failure_threshold=2,
        )
        
        # Create manager and add tasks
        manager = BackgroundTaskManager()
        manager.add_task("cleanup", cleanup_task)
        manager.add_task("health_check", health_check_task)
        
        try:
            # Start all tasks
            await manager.start_all()
            
            # Wait for tasks to run
            await asyncio.sleep(0.3)
            
            # Check status
            status = manager.get_status()
            assert status["manager_running"] is True
            assert len(status["tasks"]) == 2
            
            # Verify tasks are running
            assert cleanup_task.is_running() is True
            assert health_check_task.consecutive_failures == 0
            
            # Verify cleanup was called
            assert mock_storage.cleanup_expired_images.call_count >= 1
            
        finally:
            # Stop all tasks
            await manager.stop_all()
            
            # Verify tasks stopped
            assert cleanup_task.is_running() is False
            assert health_check_task.running is False
    
    @pytest.mark.asyncio
    async def test_task_manager_error_isolation(self):
        """Test that errors in one task don't affect others."""
        # Create one failing task and one successful task
        failing_task = MagicMock()
        failing_task.start = AsyncMock(side_effect=Exception("Failing task"))
        failing_task.stop = AsyncMock()
        
        success_task = MagicMock()
        success_task.start = AsyncMock()
        success_task.stop = AsyncMock()
        
        manager = BackgroundTaskManager()
        manager.add_task("failing", failing_task)
        manager.add_task("success", success_task)
        
        # Start all tasks - should not raise exception
        await manager.start_all()
        
        # Both should have been attempted
        failing_task.start.assert_called_once()
        success_task.start.assert_called_once()
        
        # Stop all tasks
        await manager.stop_all()
        
        # Both should be stopped
        failing_task.stop.assert_called_once()
        success_task.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_task_performance(self, mock_storage):
        """Test cleanup task performance with multiple runs."""
        mock_storage.cleanup_expired_images.return_value = 10
        
        cleanup_task = CleanupTask(
            storage=mock_storage,
            interval=0.05,  # 50ms interval
            ttl=3600,
        )
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            await cleanup_task.start()
            
            # Wait for multiple cleanup cycles
            await asyncio.sleep(0.3)
            
            end_time = asyncio.get_event_loop().time()
            elapsed = end_time - start_time
            
            # Should have run multiple times
            call_count = mock_storage.cleanup_expired_images.call_count
            
            # Verify reasonable performance (at least 4 calls in 300ms with 50ms interval)
            assert call_count >= 4
            
            # Verify timing is reasonable (not too slow)
            assert elapsed < 0.5  # Should complete within 500ms
            
        finally:
            await cleanup_task.stop()