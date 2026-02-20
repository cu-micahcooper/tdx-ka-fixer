# backend/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler = BackgroundScheduler()

def start_scheduler(cron_expression: str, job_fn) -> None:
    parts = cron_expression.split()
    trigger = CronTrigger(
        minute=parts[0], hour=parts[1],
        day=parts[2], month=parts[3], day_of_week=parts[4],
    )
    _scheduler.add_job(job_fn, trigger=trigger, id="heuristic_scan",
                       replace_existing=True)
    _scheduler.start()

def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown()
