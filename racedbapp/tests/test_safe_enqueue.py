from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from racedbapp import tasks


def make_task(name="fake_task", delay_return=None):
    task = MagicMock()
    task.name = name
    task.delay.return_value = delay_return
    return task


class SafeEnqueueTests(SimpleTestCase):
    def test_enqueues_and_returns_result_when_broker_up(self):
        task = make_task(delay_return="AsyncResult")
        with patch.object(tasks, "logger") as mock_logger:
            result = tasks.safe_enqueue(task, "arg1", kwarg=2)
        self.assertEqual(result, "AsyncResult")
        task.delay.assert_called_once_with("arg1", kwarg=2)
        mock_logger.info.assert_called_once()
        self.assertIn("fake_task", mock_logger.info.call_args[0][0])

    def test_returns_none_when_broker_down(self):
        task = make_task()
        task.delay.side_effect = ConnectionError("connection refused")
        with patch.object(tasks, "logger") as mock_logger:
            result = tasks.safe_enqueue(task)
        self.assertIsNone(result)
        self.assertEqual(mock_logger.warning.call_count, 1)
        self.assertIn("Could not enqueue task", mock_logger.warning.call_args[0][0])
        self.assertIn("fake_task", mock_logger.warning.call_args[0][0])
