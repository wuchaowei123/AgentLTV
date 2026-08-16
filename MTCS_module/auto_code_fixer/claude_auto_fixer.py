#!/usr/bin/env python3
"""
Claude Code Auto Fixer
Uses Anthropic Claude API to automatically fix Python code errors
"""

import subprocess
import os
import sys
import time
import json
from pathlib import Path
import requests

class ClaudeAutoFixer:
    def __init__(self):
        self.max_attempts = 3
        self.api_base = os.getenv('ANTHROPIC_BASE_URL', 'http://litellm.aviagames.net')
        self.api_key = os.getenv('ANTHROPIC_AUTH_TOKEN', 'sk-1gcvcMUA8g8aNy7y_FRfXg')
        self.model = 'gpt-5'
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_AUTH_TOKEN environment variable not set")
        
        print(f"✅ Claude Auto Fixer initialized")
        print(f"   API Base: {self.api_base}")
        print(f"   Model: {self.model}")
        
    def execute_python_file(self, file_path):
        """Execute Python file and return results"""
        try:
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Execution timed out (300 seconds)"
        except Exception as e:
            return False, "", str(e)
    
    def fix_code_with_claude(self, file_path, error_msg):
        """Use Claude API to fix code"""
        try:
            # Read original code
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Build fix prompt
            prompt = f"""I have a Python code file that is producing an error. Please help me fix it.

Original code:
```python
{code}
```

Error message:
```
{error_msg}
```

Please provide the complete fixed code. Return ONLY the Python code without any explanation or markdown formatting. The code should be directly executable."""
            
            # Call Claude API
            print("🤖 Using Claude to analyze and fix code...")
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 4000,
                'temperature': 1.0  # gpt-5 via litellm only supports temperature=1
            }
            
            response = requests.post(
                f'{self.api_base}/v1/messages',
                headers=headers,
                json=payload,
                timeout=180  # Increased to 3 minutes for litellm endpoint
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Extract the fixed code from response
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    fixed_code = response_data['choices'][0]['message']['content'].strip()
                elif 'content' in response_data and len(response_data['content']) > 0:
                    fixed_code = response_data['content'][0]['text'].strip()
                else:
                    print(f"❌ Unexpected response format: {response_data}")
                    return None
                
                # Extract code from markdown if present
                if '```python' in fixed_code:
                    start = fixed_code.find('```python') + 9
                    end = fixed_code.find('```', start)
                    if end != -1:
                        fixed_code = fixed_code[start:end].strip()
                    else:
                        fixed_code = fixed_code[start:].strip()
                elif '```' in fixed_code:
                    start = fixed_code.find('```') + 3
                    end = fixed_code.find('```', start)
                    if end != -1:
                        fixed_code = fixed_code[start:end].strip()
                    else:
                        fixed_code = fixed_code[start:].strip()
                
                return fixed_code
            else:
                print(f"❌ Claude API call failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error during fix process: {e}")
            return None
    
    def extract_score_from_output(self, stdout):
        """Extract score from output"""
        import re
        
        # Try to extract score from output
        score_patterns = [
            r'📊\s+(?:f1_score|F1|accuracy|AUC|RMSE):\s+([0-9.]+)',
            r'Score:\s+([0-9.]+)',
            r'Final score:\s+([0-9.]+)',
            r'Result:\s+([0-9.]+)',
            r'([0-9.]+)(?=\s*$)',  # Number at the end of last line
        ]
        
        for pattern in score_patterns:
            matches = re.findall(pattern, stdout, re.IGNORECASE)
            if matches:
                try:
                    return float(matches[-1])  # Take the last matching score
                except ValueError:
                    continue
        
        return 0.0
    
    def save_result_file(self, file_path, success, score, stdout, stderr):
        """Save result file in expected format"""
        # Extract node_id from file path
        node_id = None
        if 'node_' in file_path:
            node_id = file_path.split('node_')[1].split('.py')[0]
        
        if node_id:
            # Create result file path (format expected by AI system)
            result_file = f"/tmp/ai_result_{node_id}_{int(time.time())}.json"
            
            result_data = {
                'score': float(score),
                'success': success,
                'stdout': stdout,
                'stderr': stderr,
                'metric': 'f1_score',  # Default metric
                'higher_is_better': True
            }
            
            try:
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, indent=2)
                print(f"💾 Results saved to: {result_file}")
                return result_file
            except Exception as e:
                print(f"❌ Failed to save result file: {e}")
        
        return None

    def auto_fix_and_run(self, file_path):
        """Automatically fix and run code"""
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False
        
        print(f"🚀 Starting auto-fix and execution: {file_path}")
        print("=" * 50)
        
        final_stdout = ""
        final_stderr = ""
        final_success = False
        
        for attempt in range(1, self.max_attempts + 1):
            print(f"\n📍 Attempt {attempt} to execute...")
            
            # Execute code
            success, stdout, stderr = self.execute_python_file(file_path)
            
            final_stdout = stdout
            final_stderr = stderr
            final_success = success
            
            if success:
                print("✅ Code executed successfully!")
                if stdout:
                    print("\n📤 Output:")
                    print(stdout)
                
                # Extract score and save result file
                score = self.extract_score_from_output(stdout)
                self.save_result_file(file_path, True, score, stdout, stderr)
                return True
            else:
                print(f"❌ Execution failed: {stderr}")
                
                if attempt < self.max_attempts:
                    # Attempt to fix
                    print(f"\n🔧 Attempting to fix code (attempt {attempt})...")
                    
                    fixed_code = self.fix_code_with_claude(file_path, stderr)
                    
                    if fixed_code:
                        # Backup original file
                        backup_path = f"{file_path}.backup_{int(time.time())}"
                        os.rename(file_path, backup_path)
                        print(f"📁 Original file backed up as: {backup_path}")
                        
                        # Write fixed code
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_code)
                        
                        print("✏️  Fixed code saved")
                    else:
                        print("❌ Unable to get fix suggestion")
                        # Save failure result
                        self.save_result_file(file_path, False, 0.0, final_stdout, final_stderr)
                        return False
                else:
                    print(f"❌ Max attempts reached ({self.max_attempts}), fix failed")
                    # Save failure result
                    self.save_result_file(file_path, False, 0.0, final_stdout, final_stderr)
                    return False
        
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python claude_auto_fixer.py <python_file>")
        print("Example: python claude_auto_fixer.py test.py")
        sys.exit(1)
    
    file_path = sys.argv[1]
    fixer = ClaudeAutoFixer()
    
    success = fixer.auto_fix_and_run(file_path)
    
    if success:
        print("\n🎉 Task complete! Code executed successfully.")
    else:
        print("\n😞 Task failed, unable to fix code.")

if __name__ == "__main__":
    main()

