"""
User Feedback Collector for Interactive Search
===============================================

Collects user feedback during tree search to guide future mutations.
"""

import sys
import select
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import uuid


@dataclass
class UserFeedback:
    """User feedback for a node."""
    feedback_id: str
    node_id: str
    feedback_text: str
    feedback_type: str
    priority: int = 3
    applied_to_nodes: List[str] = field(default_factory=list)


class UserFeedbackCollector:
    """Collect user feedback during search."""
    
    def __init__(self, db_manager, enable_feedback: bool = True, timeout: int = 30):
        """
        Initialize feedback collector.
        
        Args:
            db_manager: DatabaseManager instance
            enable_feedback: Whether to enable feedback collection
            timeout: Timeout in seconds for user input
        """
        self.db = db_manager
        self.enable_feedback = enable_feedback
        self.timeout = timeout
        
        print(f"💬 User Feedback System initialized")
        print(f"   Enabled: {enable_feedback}")
        print(f"   Timeout: {timeout}s")
    
    def collect_feedback(
        self, 
        node_id: str, 
        score: float, 
        execution_time: float,
        code_snippet: str = ""
    ) -> Optional[UserFeedback]:
        """
        Collect user feedback for a node.
        
        Args:
            node_id: Node ID
            score: Performance score
            execution_time: Time taken to execute (seconds)
            code_snippet: First few lines of code for context
            
        Returns:
            UserFeedback object or None
        """
        if not self.enable_feedback:
            return None
        
        # Display node summary
        print("\n" + "=" * 70)
        print(f"✅ Node {node_id} completed successfully!")
        print(f"   📊 Score: {score:.4f}")
        print(f"   ⏱️  Execution time: {execution_time:.1f}s")
        
        if code_snippet:
            print(f"\n   📝 Code preview:")
            for line in code_snippet.split('\n')[:5]:
                if line.strip():
                    print(f"      {line[:80]}")
        
        print("\n" + "=" * 70)
        
        # Ask if user wants to provide feedback
        print("\n💬 Do you want to provide feedback for future mutations? (y/n)")
        print(f"   [Timeout in {self.timeout}s, default: no]")
        print("   > ", end='', flush=True)
        
        # Wait for input with timeout
        response = self._get_input_with_timeout(self.timeout)
        
        if not response or response.lower() not in ['y', 'yes']:
            print("Continuing without feedback...")
            return None
        
        # Collect feedback details
        print("\n📝 Please provide your feedback/advice:")
        print("   (Examples: 'Too slow', 'Try smaller model', 'Good but optimize batch size')")
        print("   > ", end='', flush=True)
        
        feedback_text = self._get_input_with_timeout(60)  # Longer timeout
        
        if not feedback_text:
            print("No feedback provided, continuing...")
            return None
        
        # Categorize feedback
        print("\n📂 Feedback type:")
        print("   1. Performance (speed/memory)")
        print("   2. Accuracy (improve score)")
        print("   3. Approach (algorithm/method)")
        print("   4. Other")
        print("   Select (1-4) [default: 1]: ", end='', flush=True)
        
        type_input = self._get_input_with_timeout(10)
        feedback_type_map = {
            '1': 'performance',
            '2': 'accuracy',
            '3': 'approach',
            '4': 'other'
        }
        feedback_type = feedback_type_map.get(type_input, 'performance')
        
        # Priority
        print("\n⭐ Priority (1-5, higher = more important) [default: 3]: ", end='', flush=True)
        priority_input = self._get_input_with_timeout(5)
        try:
            priority = int(priority_input) if priority_input else 3
            priority = max(1, min(5, priority))
        except ValueError:
            priority = 3
        
        # Create feedback object
        feedback = UserFeedback(
            feedback_id=str(uuid.uuid4())[:8],
            node_id=node_id,
            feedback_text=feedback_text,
            feedback_type=feedback_type,
            priority=priority,
            applied_to_nodes=[]
        )
        
        # Store in database
        self._store_feedback(feedback)
        
        print(f"\n✅ Feedback recorded: {feedback_text}")
        print(f"   Type: {feedback_type}, Priority: {priority}\n")
        
        return feedback
    
    def _get_input_with_timeout(self, timeout: int) -> Optional[str]:
        """Get user input with timeout (Unix/Linux only)."""
        try:
            # For Unix/Linux systems
            if sys.platform != "win32":
                ready, _, _ = select.select([sys.stdin], [], [], timeout)
                if ready:
                    return sys.stdin.readline().strip()
                else:
                    print("  (timeout)")
                    return None
            else:
                # For Windows, use simple input (no timeout)
                # For timeout support on Windows, would need msvcrt
                import threading
                result = [None]
                
                def get_input():
                    result[0] = input().strip()
                
                thread = threading.Thread(target=get_input)
                thread.daemon = True
                thread.start()
                thread.join(timeout)
                
                if thread.is_alive():
                    print("  (timeout)")
                    return None
                return result[0]
        except Exception as e:
            print(f"  (input error: {e})")
            return None
    
    def _store_feedback(self, feedback: UserFeedback):
        """Store feedback in database."""
        conn = self.db._get_connection()
        try:
            cursor = conn.cursor()
            
            # Check if user_feedback table exists, create if not
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    feedback_text TEXT NOT NULL,
                    feedback_type TEXT,
                    priority INTEGER DEFAULT 3,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    applied_to_nodes TEXT,
                    FOREIGN KEY (node_id) REFERENCES execution_nodes (node_id)
                )
            """)
            
            # Update execution_nodes (add column if doesn't exist)
            try:
                cursor.execute("""
                    UPDATE execution_nodes
                    SET user_feedback = ?
                    WHERE node_id = ?
                """, (feedback.feedback_text, feedback.node_id))
            except Exception:
                # Column doesn't exist, add it
                cursor.execute("ALTER TABLE execution_nodes ADD COLUMN user_feedback TEXT")
                cursor.execute("""
                    UPDATE execution_nodes
                    SET user_feedback = ?
                    WHERE node_id = ?
                """, (feedback.feedback_text, feedback.node_id))
            
            # Insert into user_feedback table
            cursor.execute("""
                INSERT INTO user_feedback (
                    feedback_id, node_id, feedback_text, 
                    feedback_type, priority
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                feedback.feedback_id,
                feedback.node_id,
                feedback.feedback_text,
                feedback.feedback_type,
                feedback.priority
            ))
            
            conn.commit()
        except Exception as e:
            print(f"⚠️ Error storing feedback: {e}")
        finally:
            conn.close()
    
    def get_feedback_for_lineage(self, node_id: str, max_depth: int = 5) -> List[UserFeedback]:
        """
        Get all user feedback from ancestor nodes.
        
        Args:
            node_id: Current node ID
            max_depth: Maximum ancestor depth to search
            
        Returns:
            List of UserFeedback objects
        """
        feedback_list = []
        current_id = node_id
        depth = 0
        
        conn = self.db._get_connection()
        try:
            cursor = conn.cursor()
            
            # Check if user_feedback table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='user_feedback'
            """)
            if not cursor.fetchone():
                return []
            
            while current_id and depth < max_depth:
                # Get feedback for current node
                cursor.execute("""
                    SELECT 
                        feedback_id, node_id, feedback_text,
                        feedback_type, priority
                    FROM user_feedback
                    WHERE node_id = ?
                """, (current_id,))
                
                row = cursor.fetchone()
                if row:
                    feedback = UserFeedback(
                        feedback_id=row[0],
                        node_id=row[1],
                        feedback_text=row[2],
                        feedback_type=row[3],
                        priority=row[4]
                    )
                    feedback_list.append(feedback)
                
                # Get parent node ID
                cursor.execute("""
                    SELECT parent_id
                    FROM execution_nodes
                    WHERE node_id = ?
                """, (current_id,))
                
                parent_row = cursor.fetchone()
                current_id = parent_row[0] if parent_row else None
                depth += 1
        
        except Exception as e:
            print(f"⚠️ Error getting feedback lineage: {e}")
        finally:
            conn.close()
        
        return feedback_list

