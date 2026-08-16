#!/usr/bin/env python3
"""
Claude Code CLI Auto Fixer
Uses Anthropic's Claude Code CLI to automatically fix and run Python code
"""

import subprocess
import os
import sys
import time
from pathlib import Path

class ClaudeCodeCLIFixer:
    def __init__(self):
        # Set environment variables
        self.api_base = os.getenv('ANTHROPIC_BASE_URL', 'http://litellm.aviagames.net')
        self.api_key = os.getenv('ANTHROPIC_AUTH_TOKEN', 'sk-1gcvcMUA8g8aNy7y_FRfXg')
        
        # Set environment for claude CLI
        os.environ['ANTHROPIC_BASE_URL'] = self.api_base
        os.environ['ANTHROPIC_AUTH_TOKEN'] = self.api_key
        
        print(f"✅ Claude Code CLI Fixer initialized")
        print(f"   API Base: {self.api_base}")
        print(f"   Claude CLI: {self._get_claude_path()}")
    
    def _get_claude_path(self):
        """Get the path to claude CLI"""
        try:
            result = subprocess.run(['which', 'claude'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            return "claude (in PATH)"
        except:
            return "claude"
    
    def auto_fix_and_run(self, file_path):
        """Use Claude Code CLI to automatically fix and run code"""
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False
        
        abs_file_path = os.path.abspath(file_path)
        
        print(f"🚀 Using Claude Code CLI to fix and run: {abs_file_path}")
        print("=" * 60)
        
        # Create the prompt for Claude Code
        prompt = f"""Please execute the Python file at {abs_file_path}.

If the code fails with an error:
1. Analyze the error message carefully
2. Fix the code by editing the file directly
3. Re-run the code to verify the fix works
4. Repeat until the code runs successfully

Important:
- Use the Edit tool to modify the file
- Use the Bash tool to run: python {abs_file_path}
- Continue until the code executes without errors
- If it's a complex fix that requires multiple changes, do them one at a time

Start by running the code first."""
        
        try:
            # Run Claude Code CLI with the prompt
            cmd = [
                'claude',
                '--print',  # Non-interactive mode
                '--dangerously-skip-permissions',  # Skip permission dialogs
                '--model', 'gpt-5',  # Use gpt-5 model
                prompt
            ]
            
            print(f"🤖 Running Claude Code CLI...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes timeout
                cwd=os.path.dirname(abs_file_path)
            )
            
            print("\n" + "=" * 60)
            print("📤 Claude Code Output:")
            print("=" * 60)
            print(result.stdout)
            
            if result.stderr:
                print("\n" + "=" * 60)
                print("⚠️  Errors/Warnings:")
                print("=" * 60)
                print(result.stderr)
            
            # Check if execution was successful
            if result.returncode == 0:
                print("\n✅ Claude Code completed successfully!")
                return True
            else:
                print(f"\n❌ Claude Code exited with code: {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"\n❌ Claude Code timed out after 30 minutes")
            return False
        except Exception as e:
            print(f"\n❌ Error running Claude Code: {e}")
            return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python claude_code_cli_fixer.py <python_file>")
        print("Example: python claude_code_cli_fixer.py test.py")
        sys.exit(1)
    
    file_path = sys.argv[1]
    fixer = ClaudeCodeCLIFixer()
    
    success = fixer.auto_fix_and_run(file_path)
    
    if success:
        print("\n🎉 Task complete! Code executed successfully.")
        sys.exit(0)
    else:
        print("\n😞 Task failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()

