from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import uuid
import time

@dataclass
class JobRecord:
    job_id: str
    name: str
    status: str = "queued"
    progress: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update(self, status: Optional[str] = None, progress: Optional[float] = None, **kwargs):
        if status:
            self.status = status
        if progress is not None:
            self.progress = max(0.0, min(1.0, progress))
        self.updated_at = time.time()
        self.metadata.update(kwargs)

class JobManager:
    def __init__(self):
        self.jobs: Dict[str, JobRecord] = {}

    def create_job(self, name: str, **metadata) -> JobRecord:
        job = JobRecord(job_id=str(uuid.uuid4()), name=name, metadata=metadata)
        self.jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        return self.jobs.get(job_id)

    def list_jobs(self) -> List[JobRecord]:
        return list(self.jobs.values())
