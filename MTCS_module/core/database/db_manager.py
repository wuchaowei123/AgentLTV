"""
SQLite Database Manager for Execution Tracking
=============================================

Handles all database operations for node execution tracking and result storage.
"""

import sqlite3
import os
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from .models import ExecutionNode


class DatabaseManager:
    """SQLite database manager for execution tracking."""
    
    def __init__(self, db_path: str = "execution_tracking.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database and tables if they don't exist."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Create execution_nodes table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS execution_nodes (
                        node_id TEXT PRIMARY KEY,
                        parent_id TEXT,
                        generation INTEGER DEFAULT 0,
                        mutation_type TEXT DEFAULT 'unknown',
                        
                        -- Code and execution
                        code TEXT NOT NULL,
                        code_file_path TEXT,
                        execution_status TEXT DEFAULT 'pending',
                        
                        -- Results
                        score REAL,
                        secondary_scores TEXT,  -- JSON
                        predictions TEXT,       -- JSON
                        
                        -- Execution details
                        execution_start_time TEXT,
                        execution_end_time TEXT,
                        execution_duration REAL,
                        error_message TEXT,
                        auto_fixes INTEGER DEFAULT 0,
                        
                        -- Metadata
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        
                        FOREIGN KEY (parent_id) REFERENCES execution_nodes (node_id)
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_status ON execution_nodes (execution_status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent_id ON execution_nodes (parent_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_score ON execution_nodes (score DESC)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON execution_nodes (created_at)")
                
                conn.commit()
                print(f"✅ Database initialized: {self.db_path}")
                
            finally:
                conn.close()
    
    def insert_node(self, node: ExecutionNode) -> bool:
        """
        Insert a new execution node.
        
        Args:
            node: ExecutionNode to insert
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                node_data = node.to_dict()
                
                columns = ', '.join(node_data.keys())
                placeholders = ', '.join(['?' for _ in node_data])
                values = list(node_data.values())
                
                cursor.execute(
                    f"INSERT INTO execution_nodes ({columns}) VALUES ({placeholders})",
                    values
                )
                conn.commit()
                return True
                
            except sqlite3.IntegrityError as e:
                print(f"❌ Failed to insert node {node.node_id}: {e}")
                return False
            finally:
                conn.close()
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing execution node.
        
        Args:
            node_id: ID of node to update
            updates: Dictionary of field updates
            
        Returns:
            True if successful, False otherwise
        """
        if not updates:
            return True
            
        # Add updated timestamp
        updates['updated_at'] = datetime.now().isoformat()
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
                values = list(updates.values()) + [node_id]
                
                cursor.execute(
                    f"UPDATE execution_nodes SET {set_clause} WHERE node_id = ?",
                    values
                )
                
                if cursor.rowcount == 0:
                    print(f"⚠️ No node found with ID: {node_id}")
                    return False
                
                conn.commit()
                return True
                
            except Exception as e:
                print(f"❌ Failed to update node {node_id}: {e}")
                return False
            finally:
                conn.close()
    
    def get_node(self, node_id: str) -> Optional[ExecutionNode]:
        """
        Get a single execution node by ID.
        
        Args:
            node_id: ID of node to retrieve
            
        Returns:
            ExecutionNode if found, None otherwise
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM execution_nodes WHERE node_id = ?", (node_id,))
                row = cursor.fetchone()
                
                if row:
                    columns = [description[0] for description in cursor.description]
                    node_data = dict(zip(columns, row))
                    return ExecutionNode.from_dict(node_data)
                
                return None
                
            finally:
                conn.close()
    
    def get_nodes_by_status(self, status: str) -> List[ExecutionNode]:
        """
        Get all nodes with a specific execution status.
        
        Args:
            status: Execution status to filter by
            
        Returns:
            List of ExecutionNode objects
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM execution_nodes WHERE execution_status = ? ORDER BY created_at",
                    (status,)
                )
                rows = cursor.fetchall()
                
                columns = [description[0] for description in cursor.description]
                nodes = []
                for row in rows:
                    node_data = dict(zip(columns, row))
                    nodes.append(ExecutionNode.from_dict(node_data))
                
                return nodes
                
            finally:
                conn.close()
    
    def get_pending_nodes(self) -> List[ExecutionNode]:
        """Get all nodes pending execution."""
        return self.get_nodes_by_status('pending')
    
    def get_failed_nodes(self) -> List[ExecutionNode]:
        """Get all nodes that failed execution."""
        return self.get_nodes_by_status('failed')
    
    def get_manual_required_nodes(self) -> List[ExecutionNode]:
        """Get all nodes requiring manual execution."""
        return self.get_nodes_by_status('manual_required')
    
    def get_completed_nodes(self) -> List[ExecutionNode]:
        """Get all successfully completed nodes."""
        return self.get_nodes_by_status('completed')
    
    def get_best_nodes(self, limit: int = 10) -> List[ExecutionNode]:
        """
        Get top performing nodes by score.
        
        Args:
            limit: Maximum number of nodes to return
            
        Returns:
            List of best ExecutionNode objects
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM execution_nodes WHERE score IS NOT NULL ORDER BY score DESC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()
                
                columns = [description[0] for description in cursor.description]
                nodes = []
                for row in rows:
                    node_data = dict(zip(columns, row))
                    nodes.append(ExecutionNode.from_dict(node_data))
                
                return nodes
                
            finally:
                conn.close()
    
    def update_execution_status(self, node_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """
        Update execution status of a node.
        
        Args:
            node_id: ID of node to update
            status: New execution status
            error_message: Optional error message for failed executions
            
        Returns:
            True if successful, False otherwise
        """
        updates = {'execution_status': status}
        
        if error_message:
            updates['error_message'] = error_message
        
        if status == 'executing':
            updates['execution_start_time'] = datetime.now().isoformat()
        elif status in ['completed', 'failed']:
            updates['execution_end_time'] = datetime.now().isoformat()
            
            # Calculate duration if start time exists
            node = self.get_node(node_id)
            if node and node.execution_start_time:
                duration = (datetime.now() - node.execution_start_time).total_seconds()
                updates['execution_duration'] = duration
        
        return self.update_node(node_id, updates)
    
    def update_execution_result(self, node_id: str, score: float, 
                              secondary_scores: Optional[Dict[str, Any]] = None,
                              predictions: Optional[List[Any]] = None,
                              auto_fixes: int = 0) -> bool:
        """
        Update execution result for a node.
        
        Args:
            node_id: ID of node to update
            score: Primary score achieved
            secondary_scores: Optional secondary scores
            predictions: Optional predictions made
            auto_fixes: Number of automatic fixes applied
            
        Returns:
            True if successful, False otherwise
        """
        updates = {
            'score': score,
            'auto_fixes': auto_fixes,
            'execution_status': 'completed'
        }
        
        if secondary_scores:
            import json
            updates['secondary_scores'] = json.dumps(secondary_scores)
        
        if predictions:
            import json
            updates['predictions'] = json.dumps(predictions)
        
        # Set end time and calculate duration
        updates['execution_end_time'] = datetime.now().isoformat()
        
        node = self.get_node(node_id)
        if node and node.execution_start_time:
            duration = (datetime.now() - node.execution_start_time).total_seconds()
            updates['execution_duration'] = duration
        
        return self.update_node(node_id, updates)
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Returns:
            Dictionary with execution statistics
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Get status counts
                cursor.execute("SELECT execution_status, COUNT(*) FROM execution_nodes GROUP BY execution_status")
                status_counts = dict(cursor.fetchall())
                
                # Get best score
                cursor.execute("SELECT MAX(score) FROM execution_nodes WHERE score IS NOT NULL")
                best_score = cursor.fetchone()[0]
                
                # Get average score
                cursor.execute("SELECT AVG(score) FROM execution_nodes WHERE score IS NOT NULL")
                avg_score = cursor.fetchone()[0]
                
                # Get total nodes
                cursor.execute("SELECT COUNT(*) FROM execution_nodes")
                total_nodes = cursor.fetchone()[0]
                
                return {
                    'total_nodes': total_nodes,
                    'status_counts': status_counts,
                    'best_score': best_score,
                    'average_score': avg_score,
                    'success_rate': status_counts.get('completed', 0) / max(total_nodes, 1) * 100
                }
                
            finally:
                conn.close()
    
    def cleanup_old_nodes(self, days: int = 7) -> int:
        """
        Remove nodes older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of nodes removed
        """
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM execution_nodes WHERE created_at < ?",
                    (datetime.fromtimestamp(cutoff_date).isoformat(),)
                )
                removed_count = cursor.rowcount
                conn.commit()
                
                print(f"🧹 Cleaned up {removed_count} old nodes")
                return removed_count
                
            finally:
                conn.close()
    
    def export_results(self, output_file: str) -> bool:
        """
        Export all results to a CSV file.
        
        Args:
            output_file: Path to output CSV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import pandas as pd
            
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    df = pd.read_sql_query("SELECT * FROM execution_nodes", conn)
                    df.to_csv(output_file, index=False)
                    print(f"📊 Results exported to: {output_file}")
                    return True
                finally:
                    conn.close()
                    
        except Exception as e:
            print(f"❌ Failed to export results: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM execution_nodes")
                total_nodes = cursor.fetchone()[0]
                
                # Get status counts
                cursor.execute("SELECT execution_status, COUNT(*) FROM execution_nodes GROUP BY execution_status")
                status_counts = dict(cursor.fetchall())
                
                # Get best score
                cursor.execute("SELECT MAX(score) FROM execution_nodes WHERE score IS NOT NULL")
                best_score_result = cursor.fetchone()[0]
                best_score = best_score_result if best_score_result is not None else None
                
                # Get average score  
                cursor.execute("SELECT AVG(score) FROM execution_nodes WHERE score IS NOT NULL")
                avg_score_result = cursor.fetchone()[0]
                average_score = avg_score_result if avg_score_result is not None else None
                
                # Calculate success rate
                completed_count = status_counts.get('completed', 0)
                success_rate = (completed_count / total_nodes * 100) if total_nodes > 0 else 0.0
                
                return {
                    'total_nodes': total_nodes,
                    'status_counts': status_counts,
                    'best_score': best_score,
                    'average_score': average_score,
                    'success_rate': success_rate
                }
                
            except Exception as e:
                print(f"❌ Error getting stats: {e}")
                return {'total_nodes': 0, 'status_counts': {}, 'best_score': None, 'average_score': None, 'success_rate': 0.0}
            finally:
                conn.close()
    
    def get_all_nodes(self) -> List[ExecutionNode]:
        """Get all execution nodes."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM execution_nodes")
                rows = cursor.fetchall()
                
                # Get column names
                cursor.execute("PRAGMA table_info(execution_nodes)")
                columns = [col[1] for col in cursor.fetchall()]
                
                nodes = []
                for row in rows:
                    node_data = dict(zip(columns, row))
                    nodes.append(ExecutionNode.from_dict(node_data))
                
                return nodes
                
            except Exception as e:
                print(f"❌ Error getting all nodes: {e}")
                return []
            finally:
                conn.close()
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics (alias for get_stats)."""
        return self.get_stats()
    
    def get_failed_nodes(self) -> List[ExecutionNode]:
        """Get nodes that failed execution."""
        return self.get_nodes_by_status('failed')
    
    def get_manual_required_nodes(self) -> List[ExecutionNode]:
        """Get nodes requiring manual execution."""
        return self.get_nodes_by_status('manual_required')
    
    def cleanup_old_nodes(self, days: int) -> int:
        """Clean up nodes older than specified days."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                from datetime import datetime, timedelta
                cutoff_date = datetime.now() - timedelta(days=days)
                cutoff_str = cutoff_date.isoformat()
                
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM execution_nodes WHERE created_at < ?", (cutoff_str,))
                count = cursor.fetchone()[0]
                
                cursor.execute("DELETE FROM execution_nodes WHERE created_at < ?", (cutoff_str,))
                conn.commit()
                
                print(f"🧹 Cleaned up {count} nodes older than {days} days")
                return count
                
            except Exception as e:
                print(f"❌ Error cleaning up old nodes: {e}")
                return 0
            finally:
                conn.close()