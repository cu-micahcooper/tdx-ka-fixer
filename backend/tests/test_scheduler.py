# backend/tests/test_scheduler.py
from unittest.mock import MagicMock, patch, PropertyMock
import scheduler as sched_module
from apscheduler.schedulers.background import BackgroundScheduler

def test_start_and_stop_scheduler():
    mock_fn = MagicMock()
    with patch.object(sched_module._scheduler, "add_job") as mock_add, \
         patch.object(sched_module._scheduler, "start") as mock_start, \
         patch.object(sched_module._scheduler, "shutdown") as mock_stop, \
         patch.object(BackgroundScheduler, "running", new_callable=PropertyMock, return_value=True):
        sched_module.start_scheduler("0 2 * * *", mock_fn)
        mock_add.assert_called_once()
        mock_start.assert_called_once()
        sched_module.stop_scheduler()
        mock_stop.assert_called_once()
