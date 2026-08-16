"""
Webhook notification system for manual execution alerts.
Sends notifications to Feishu (Lark) when manual execution is required.
"""

import requests
import json
import os
from typing import Optional, Dict, Any
from pathlib import Path


class WebhookNotifier:
    """Send notifications via webhook when manual execution is required."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize webhook notifier.
        
        Args:
            webhook_url: Feishu webhook URL. If not provided, reads from environment
                        variable MANUAL_EXECUTION_WEBHOOK_URL
        """
        self.webhook_url = webhook_url or os.environ.get(
            'MANUAL_EXECUTION_WEBHOOK_URL',
            'https://open.feishu.cn/open-apis/bot/v2/hook/8580b5c3-7f23-462b-8991-87c2649ae918'
        )
        self.enabled = bool(self.webhook_url)
        
    def send_manual_execution_alert(
        self,
        node_id: str,
        code_file: str,
        error_message: str,
        db_path: str,
        project_dir: str = "/home/jupyter/MTCS_module"
    ) -> bool:
        """
        Send alert when manual execution is required.
        
        Args:
            node_id: ID of the node requiring manual execution
            code_file: Path to the code file
            error_message: Error message from auto-fixer
            db_path: Path to database file
            project_dir: Project directory path
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.enabled:
            print("⚠️  Webhook notifications disabled (no webhook URL configured)")
            return False
        
        # Send manual execution instructions
        message_text = self._format_manual_execution_message(
            node_id, code_file, error_message, db_path, project_dir
        )
        success1 = self._send_feishu_message(message_text)
        
        # Send Claude Code prompt
        claude_prompt = self._format_claude_code_prompt(
            node_id, code_file, project_dir
        )
        success2 = self._send_feishu_message(claude_prompt)
        
        return success1 and success2
    
    def _format_manual_execution_message(
        self,
        node_id: str,
        code_file: str,
        error_message: str,
        db_path: str,
        project_dir: str
    ) -> str:
        """Format the manual execution alert message."""
        
        # Truncate error if too long
        if len(error_message) > 300:
            error_message = error_message[:300] + "... (truncated)"
        
        message = f"""🚨 MANUAL EXECUTION REQUIRED 🚨

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Node ID: {node_id}
📁 Code File: {code_file}
🗄️  Database: {db_path}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ Error:
{error_message}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 MANUAL EXECUTION STEPS:

1️⃣ Navigate to project:
   cd {project_dir}

2️⃣ Activate environment:
   conda activate pytorch

3️⃣ Edit the code (fix the bug):
   nano {code_file}

4️⃣ Run the code:
   python {code_file}

5️⃣ Update result (replace <YOUR_SCORE>):
   
   python manual_update_result.py \\
     --node-id {node_id} \\
     --score <YOUR_SCORE> \\
     --success \\
     --code-file {code_file} \\
     --db-path {db_path}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 MANUAL UPDATE SCRIPT OPTIONS:

✅ For Success:
   python manual_update_result.py \\
     --node-id {node_id} \\
     --score 0.91 \\
     --success \\
     --code-file {code_file} \\
     --db-path {db_path}

❌ For Failure:
   python manual_update_result.py \\
     --node-id {node_id} \\
     --error "Error description" \\
     --db-path {db_path}

📈 With Secondary Scores:
   python manual_update_result.py \\
     --node-id {node_id} \\
     --score 0.91 \\
     --success \\
     --secondary '{{"precision": 0.89, "recall": 0.93}}' \\
     --db-path {db_path}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ System is waiting for your manual update...
"""
        return message
    
    def _format_claude_code_prompt(
        self,
        node_id: str,
        code_file: str,
        project_dir: str
    ) -> str:
        """Format the Claude Code prompt for fixing and running code."""
        
        # Determine JSON result file path
        json_result_file = f"/tmp/ai_result_{node_id}_manual.json"
        
        prompt = f"""🤖 CLAUDE CODE PROMPT FOR MANUAL FIXING:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Task: Fix and Run Code
📁 Code File: {code_file}
🆔 Node ID: {node_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 CLAUDE CODE INSTRUCTIONS:

Read this file: {code_file}

Check if the code has any errors, fix them, and run the code.

After running the code successfully:
1. The code should generate a JSON result at: {json_result_file}
2. The JSON file should contain:
   - "score": The F1 score (float)
   - "success": true
   - "predictions": (optional) test predictions
   - "error": null

Expected JSON format:
{{
    "score": 0.9156,
    "success": true,
    "predictions": [...],
    "error": null
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 HOW TO USE WITH CLAUDE CODE:

Option 1 - Direct Prompt:
   claude -p "Read {code_file}, check for errors, fix and run it. Make sure it generates {json_result_file} with the score."

Option 2 - Interactive Mode:
   claude
   > Read {code_file}
   > Check for errors and fix them
   > Run the code
   > Verify {json_result_file} was created

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ IMPORTANT:
- Make sure the code generates the JSON result file
- JSON file must have "score" and "success" fields
- After completion, run the manual_update_result.py command
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return prompt
    
    def _send_feishu_message(self, text: str) -> bool:
        """
        Send message to Feishu webhook.
        
        Args:
            text: Message text to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        message = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(message),
                timeout=10
            )
            response.raise_for_status()
            print(f"✅ Manual execution alert sent via webhook")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send webhook notification: {e}")
            return False
    
    def send_completion_alert(
        self,
        node_id: str,
        score: float,
        success: bool
    ) -> bool:
        """
        Send alert when manual execution is completed.
        
        Args:
            node_id: ID of the completed node
            score: Score achieved
            success: Whether execution was successful
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        if success:
            message_text = f"""✅ MANUAL EXECUTION COMPLETED

Node ID: {node_id}
Score: {score:.4f}
Status: SUCCESS

Tree search will continue with this result.
"""
        else:
            message_text = f"""❌ MANUAL EXECUTION FAILED

Node ID: {node_id}
Status: FAILED

Tree search will skip this node and continue.
"""
        
        return self._send_feishu_message(message_text)
    
    def send_best_score_alert(
        self,
        score: float,
        improvement: float,
        node_id: str
    ) -> bool:
        """
        Send alert when a new best score is found.
        
        Args:
            score: New best score
            improvement: Improvement over previous best
            node_id: ID of the node with best score
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        message_text = f"""🎉 NEW BEST SCORE ACHIEVED!

Score: {score:.4f}
Improvement: +{improvement:.4f} (+{improvement*100:.2f}%)
Node ID: {node_id}

Keep going! 🚀
"""
        
        return self._send_feishu_message(message_text)

