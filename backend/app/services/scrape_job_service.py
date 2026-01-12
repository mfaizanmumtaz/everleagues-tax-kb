"""Scrape Job service for PostgreSQL."""

from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from ..db_models.scrape_job import (
    ScrapeJob,
    ScrapeJobLog,
    JobStatus,
    LogLevel,
)


class ScrapeJobService:
    """Service for scrape job operations using PostgreSQL."""
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
    
    def create_job(
        self,
        scrape_url_id: UUID,
        triggered_by: str = "manual",
    ) -> ScrapeJob:
        """
        Create a new scrape job.
        
        Args:
            scrape_url_id: ID of the URL to scrape
            triggered_by: What triggered the job (manual, scheduler, api)
        
        Returns:
            Created ScrapeJob object
        """
        job = ScrapeJob(
            scrape_url_id=scrape_url_id,
            status=JobStatus.PENDING,
            progress_current=0,
            progress_total=0,
            progress_message="Job created",
            triggered_by=triggered_by,
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def get_job(self, job_id: UUID) -> Optional[ScrapeJob]:
        """Get a job by ID."""
        return self.db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    
    def get_jobs_for_url(
        self,
        scrape_url_id: UUID,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[ScrapeJob], int]:
        """Get jobs for a specific URL."""
        query = self.db.query(ScrapeJob).filter(
            ScrapeJob.scrape_url_id == scrape_url_id
        )
        
        total = query.count()
        offset = (page - 1) * limit
        jobs = query.order_by(ScrapeJob.created_at.desc()).offset(offset).limit(limit).all()
        
        return jobs, total
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        triggered_by: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[ScrapeJob], int]:
        """
        List jobs with filters and pagination.
        
        Returns:
            Tuple of (jobs list, total count)
        """
        query = self.db.query(ScrapeJob)
        
        if status:
            query = query.filter(ScrapeJob.status == status)
        if triggered_by:
            query = query.filter(ScrapeJob.triggered_by == triggered_by)
        
        total = query.count()
        offset = (page - 1) * limit
        jobs = query.order_by(ScrapeJob.created_at.desc()).offset(offset).limit(limit).all()
        
        return jobs, total
    
    def start_job(self, job_id: UUID) -> Optional[ScrapeJob]:
        """Mark a job as started."""
        job = self.get_job(job_id)
        if not job:
            return None
        
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.progress_message = "Job started"
        
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def update_progress(
        self,
        job_id: UUID,
        current: int,
        total: int,
        message: Optional[str] = None,
    ) -> Optional[ScrapeJob]:
        """Update job progress."""
        job = self.get_job(job_id)
        if not job:
            return None
        
        job.progress_current = current
        job.progress_total = total
        if message:
            job.progress_message = message
        
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def complete_job(
        self,
        job_id: UUID,
        documents_created: int = 0,
        documents_updated: int = 0,
        documents_failed: int = 0,
        chunks_created: int = 0,
    ) -> Optional[ScrapeJob]:
        """Mark a job as completed."""
        job = self.get_job(job_id)
        if not job:
            return None
        
        now = datetime.utcnow()
        
        job.status = JobStatus.COMPLETED
        job.completed_at = now
        job.progress_message = "Job completed"
        job.documents_created = documents_created
        job.documents_updated = documents_updated
        job.documents_failed = documents_failed
        job.chunks_created = chunks_created
        
        # Calculate duration
        if job.started_at:
            duration = (now - job.started_at).total_seconds()
            job.duration_seconds = int(duration)
        
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def fail_job(
        self,
        job_id: UUID,
        error_message: str,
        error_details: Optional[dict] = None,
    ) -> Optional[ScrapeJob]:
        """Mark a job as failed."""
        job = self.get_job(job_id)
        if not job:
            return None
        
        now = datetime.utcnow()
        
        job.status = JobStatus.FAILED
        job.completed_at = now
        job.error_message = error_message
        job.error_details = error_details
        job.progress_message = f"Job failed: {error_message}"
        
        # Calculate duration
        if job.started_at:
            duration = (now - job.started_at).total_seconds()
            job.duration_seconds = int(duration)
        
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def cancel_job(self, job_id: UUID) -> Optional[ScrapeJob]:
        """Cancel a job."""
        job = self.get_job(job_id)
        if not job:
            return None
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            return job  # Can't cancel already finished jobs
        
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        job.progress_message = "Job cancelled"
        
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def add_log(
        self,
        job_id: UUID,
        level: LogLevel,
        message: str,
        details: Optional[dict] = None,
    ) -> ScrapeJobLog:
        """Add a log entry for a job."""
        log = ScrapeJobLog(
            job_id=job_id,
            level=level,
            message=message,
            details=details,
        )
        
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        
        return log
    
    def get_job_logs(
        self,
        job_id: UUID,
        level: Optional[LogLevel] = None,
        page: int = 1,
        limit: int = 100,
    ) -> Tuple[List[ScrapeJobLog], int]:
        """Get logs for a job."""
        query = self.db.query(ScrapeJobLog).filter(ScrapeJobLog.job_id == job_id)
        
        if level:
            query = query.filter(ScrapeJobLog.level == level)
        
        total = query.count()
        offset = (page - 1) * limit
        logs = query.order_by(ScrapeJobLog.created_at.asc()).offset(offset).limit(limit).all()
        
        return logs, total
    
    def get_running_jobs(self) -> List[ScrapeJob]:
        """Get all currently running jobs."""
        return self.db.query(ScrapeJob).filter(
            ScrapeJob.status == JobStatus.RUNNING
        ).all()
    
    def to_dict(self, job: ScrapeJob) -> dict:
        """Convert ScrapeJob to dictionary for API response."""
        return {
            "id": str(job.id),
            "scrape_url_id": str(job.scrape_url_id),
            "status": job.status.value if job.status else "pending",
            "progress_current": job.progress_current or 0,
            "progress_total": job.progress_total or 0,
            "progress_message": job.progress_message,
            "documents_created": job.documents_created or 0,
            "documents_updated": job.documents_updated or 0,
            "documents_failed": job.documents_failed or 0,
            "chunks_created": job.chunks_created or 0,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "duration_seconds": job.duration_seconds,
            "error_message": job.error_message,
            "triggered_by": job.triggered_by,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }

