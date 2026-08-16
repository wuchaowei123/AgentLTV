"""
Database Models for Execution Tracking
=====================================

SQLite models for storing node execution data and results.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json


@dataclass
class ExecutionNode:
    """Model for execution node data."""
    
    # Node identification
    node_id: str
    parent_id: Optional[str] = None
    generation: int = 0
    mutation_type: str = "unknown"
    
    # Code and execution
    code: str = ""
    code_file_path: Optional[str] = None
    execution_status: str = "pending"  # pending, executing, completed, failed, manual_required
    
    # Results
    score: Optional[float] = None
    secondary_scores: Optional[Dict[str, Any]] = None
    predictions: Optional[List[Any]] = None
    
    # Execution details
    execution_start_time: Optional[datetime] = None
    execution_end_time: Optional[datetime] = None
    execution_duration: Optional[float] = None
    error_message: Optional[str] = None
    auto_fixes: int = 0
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set default timestamps."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'node_id': self.node_id,
            'parent_id': self.parent_id,
            'generation': self.generation,
            'mutation_type': self.mutation_type,
            'code': self.code,
            'code_file_path': self.code_file_path,
            'execution_status': self.execution_status,
            'score': self.score,
            'secondary_scores': json.dumps(self.secondary_scores) if self.secondary_scores else None,
            'predictions': json.dumps(self.predictions) if self.predictions else None,
            'execution_start_time': self.execution_start_time.isoformat() if self.execution_start_time else None,
            'execution_end_time': self.execution_end_time.isoformat() if self.execution_end_time else None,
            'execution_duration': self.execution_duration,
            'error_message': self.error_message,
            'auto_fixes': self.auto_fixes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionNode':
        """Create instance from database dictionary."""
        # Parse JSON fields
        secondary_scores = json.loads(data['secondary_scores']) if data['secondary_scores'] else None
        predictions = json.loads(data['predictions']) if data['predictions'] else None
        
        # Parse datetime fields
        execution_start_time = datetime.fromisoformat(data['execution_start_time']) if data['execution_start_time'] else None
        execution_end_time = datetime.fromisoformat(data['execution_end_time']) if data['execution_end_time'] else None
        created_at = datetime.fromisoformat(data['created_at']) if data['created_at'] else None
        updated_at = datetime.fromisoformat(data['updated_at']) if data['updated_at'] else None
        
        return cls(
            node_id=data['node_id'],
            parent_id=data['parent_id'],
            generation=data['generation'],
            mutation_type=data['mutation_type'],
            code=data['code'],
            code_file_path=data['code_file_path'],
            execution_status=data['execution_status'],
            score=data['score'],
            secondary_scores=secondary_scores,
            predictions=predictions,
            execution_start_time=execution_start_time,
            execution_end_time=execution_end_time,
            execution_duration=data['execution_duration'],
            error_message=data['error_message'],
            auto_fixes=data['auto_fixes'],
            created_at=created_at,
            updated_at=updated_at
        )
    
    def is_completed(self) -> bool:
        """Check if execution is completed successfully."""
        return self.execution_status == 'completed' and self.score is not None
    
    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self.execution_status in ['failed', 'manual_required']
    
    def is_pending(self) -> bool:
        """Check if execution is pending."""
        return self.execution_status == 'pending'
    
    def requires_manual_execution(self) -> bool:
        """Check if manual execution is required."""
        return self.execution_status == 'manual_required'