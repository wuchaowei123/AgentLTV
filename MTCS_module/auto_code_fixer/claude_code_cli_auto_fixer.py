#!/usr/bin/env python3
"""
Claude Code CLI Auto-Fixer
Uses Claude Code CLI to iteratively fix code errors
"""

import subprocess
import sys
import os
import time
import re

class ClaudeCodeCLIAutoFixer:
    def __init__(self, model="gpt-5", max_attempts=2):
        self.model = model
        self.max_attempts = max_attempts
        self.setup_environment()
    
    def setup_environment(self):
        """Setup environment variables for Claude Code CLI"""
        # These are read from environment or use defaults
        self.api_base = os.environ.get('ANTHROPIC_BASE_URL', 'http://litellm.aviagames.net')
        self.api_token = os.environ.get('ANTHROPIC_AUTH_TOKEN', 'sk-1gcvcMUA8g8aNy7y_FRfXg')
        
        # Set environment for subprocess
        self.env = os.environ.copy()
        self.env['ANTHROPIC_BASE_URL'] = self.api_base
        self.env['ANTHROPIC_AUTH_TOKEN'] = self.api_token
        self.env['ANTHROPIC_MODEL'] = self.model
        self.env['ANTHROPIC_DEFAULT_HAIKU_MODEL'] = self.model
        self.env['CLAUDE_CODE_SUBAGENT_MODEL'] = self.model
        
        print(f"✅ Claude Code CLI Auto Fixer initialized")
        print(f"   API Base: {self.api_base}")
        print(f"   Model: {self.model}")
    
    def run_code(self, code_file, timeout=300, conda_env="pytorch"):
        """Run the code file and capture output/errors"""
        print(f"\n🔄 Running {code_file}...")
        print(f"   ⏱️  Timeout: {timeout} seconds")
        print(f"   🐍 Conda env: {conda_env}")
        print(f"   📍 Working directory: {os.path.dirname(os.path.abspath(code_file)) or '.'}")
        start_time = time.time()
        
        # Get absolute path and separate directory and filename
        abs_path = os.path.abspath(code_file)
        code_dir = os.path.dirname(abs_path)
        code_name = os.path.basename(abs_path)
        
        cmd = f'source ~/.bashrc && conda activate {conda_env} && cd {code_dir} && timeout {timeout} python {code_name} 2>&1'
        print(f"   💻 Command: {cmd[:150]}...")
        print(f"   ⏳ Starting execution...")
        sys.stdout.flush()
        
        result = subprocess.run(
            ['bash', '-c', cmd],
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - start_time
        print(f"   ✓ Execution completed in {elapsed:.1f} seconds")
        print(f"   📊 Exit code: {result.returncode}")
        print(f"   📝 Output length: {len(result.stdout + result.stderr)} characters")
        sys.stdout.flush()
        
        return result.returncode, result.stdout + result.stderr
    
    def extract_error_info(self, output):
        """Extract error information from output"""
        lines = output.strip().split('\n')
        
        # Look for common error patterns
        error_line = None
        error_type = None
        error_message = None
        
        for i, line in enumerate(lines):
            if 'Error:' in line or 'Exception:' in line:
                error_type = line.strip()
                if i + 1 < len(lines):
                    error_message = lines[i + 1].strip()
            elif 'line' in line.lower() and ('file' in line.lower() or '.py' in line):
                # Extract line number
                match = re.search(r'line (\d+)', line, re.IGNORECASE)
                if match:
                    error_line = match.group(1)
            elif line.startswith('  File'):
                # Extract line number from traceback
                match = re.search(r'line (\d+)', line)
                if match:
                    error_line = match.group(1)
        
        # Get last few lines which usually contain the error
        last_lines = '\n'.join(lines[-10:])
        
        return {
            'error_line': error_line,
            'error_type': error_type,
            'error_message': error_message,
            'last_output': last_lines
        }
    
    def ask_claude_to_fix(self, code_file, error_info, timeout=120):
        """Use Claude Code CLI to suggest a fix with specific line changes"""
        print(f"\n🤖 Asking Claude Code CLI for fix suggestion...")
        print(f"   📁 File: {code_file}")
        print(f"   ⏱️  Timeout: {timeout} seconds")
        print(f"   🔍 Error line: {error_info['error_line']}")
        sys.stdout.flush()
        
        start_time = time.time()
        
        # Construct prompt WITHOUT asking to read file (to avoid temperature=0 issues)
        prompt = f"""Fix this Python error:

Error Output:
{error_info['last_output']}

Suggest the specific fix needed. Be concise."""
        
        print(f"   📝 Prompt length: {len(prompt)} characters")
        cmd = f'claude -p "{prompt}" --model {self.model}'
        print(f"   ⏳ Sending request to Claude Code CLI...")
        sys.stdout.flush()
        
        try:
            result = subprocess.run(
                ['bash', '-c', cmd],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self.env
            )
            
            elapsed = time.time() - start_time
            print(f"   ✓ Claude response received in {elapsed:.1f} seconds")
            
            if result.returncode == 0:
                response = result.stdout.strip()
                print(f"   📊 Response length: {len(response)} characters")
                print(f"   💡 Claude's suggestion (first 300 chars):")
                print(f"      {response[:300]}...")
                sys.stdout.flush()
                return response
            else:
                print(f"   ⚠️  Claude Code CLI failed (exit code: {result.returncode})")
                print(f"   ❌ Error: {result.stderr[:200]}")
                sys.stdout.flush()
                return None
                
        except subprocess.TimeoutExpired:
            print(f"   ⚠️  Claude Code CLI timed out after {timeout} seconds")
            sys.stdout.flush()
            return None
    
    def parse_and_apply_fix(self, code_file, fix_suggestion):
        """Parse Claude's fix suggestion and apply it to the file"""
        if not fix_suggestion:
            print(f"\n🔧 No fix suggestion to apply")
            return False
        
        print(f"\n🔧 Attempting to apply fix automatically...")
        print(f"   📁 File: {code_file}")
        print(f"   🔍 Analyzing suggestion for patterns...")
        sys.stdout.flush()
        
        # Try to extract line number and replacement from various formats
        # Format 1: LINE X: old content / REPLACE WITH: new content
        # Format 2: Change line X from "old" to "new"
        # Format 3: Direct content mention
        
        try:
            # Read current file
            print(f"   📖 Reading current file...")
            with open(code_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"   ✓ File has {len(lines)} lines")
            sys.stdout.flush()
            
            # Simple heuristic: look for common error patterns and fix them
            # Example: 'label' -> 'labels', variable typos, etc.
            
            # Check for common patterns in the suggestion
            print(f"   🔎 Checking for 'label' -> 'labels' pattern...")
            if "'label'" in fix_suggestion.lower() and "'labels'" in fix_suggestion.lower():
                # Fix column name issue
                for i, line in enumerate(lines):
                    if "train_df['label']" in line:
                        print(f"   ✓ Found 'train_df['label']' on line {i+1}")
                        lines[i] = line.replace("train_df['label']", "train_df['labels']")
                        print(f"   ✓ Replaced with 'train_df['labels']'")
                        
                        # Write back
                        print(f"   💾 Writing changes to file...")
                        with open(code_file, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        print(f"   ✅ Fix applied successfully!")
                        sys.stdout.flush()
                        return True
            
            # Look for .to() method fix
            print(f"   🔎 Checking for '.to(device)' pattern...")
            if ".to(device)" in fix_suggestion and "sentence" in fix_suggestion.lower():
                for i, line in enumerate(lines):
                    if ".to(device)" in line and "embedding_model" in line:
                        # Comment out the problematic line
                        print(f"   ✓ Found '.to(device)' on line {i+1}")
                        lines[i] = "# " + line
                        print(f"   ✓ Commented out the line")
                        
                        # Write back
                        print(f"   💾 Writing changes to file...")
                        with open(code_file, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        print(f"   ✅ Fix applied successfully!")
                        sys.stdout.flush()
                        return True
            
            print(f"   ⚠️  Could not auto-apply fix - no pattern matched")
            print(f"   📄 Full suggestion: {fix_suggestion[:400]}...")
            sys.stdout.flush()
            return False
            
        except Exception as e:
            print(f"   ⚠️  Error applying fix: {str(e)}")
            sys.stdout.flush()
            return False
    
    def auto_fix_and_run(self, code_file, run_timeout=300):
        """
        Iteratively run code and fix errors using Claude Code CLI
        """
        print(f"\n{'=' * 70}")
        print(f"🚀 STARTING AUTO-FIX-AND-RUN WORKFLOW")
        print(f"{'=' * 70}")
        print(f"📁 File: {code_file}")
        print(f"🔢 Max attempts: {self.max_attempts}")
        print(f"⏱️  Run timeout: {run_timeout} seconds")
        print(f"🤖 Model: {self.model}")
        print(f"{'=' * 70}\n")
        sys.stdout.flush()
        
        for attempt in range(1, self.max_attempts + 1):
            print(f"\n{'─' * 70}")
            print(f"📍 ATTEMPT {attempt}/{self.max_attempts}")
            print(f"{'─' * 70}")
            sys.stdout.flush()
            
            # Run the code
            return_code, output = self.run_code(code_file, timeout=run_timeout)
            
            if return_code == 0:
                print(f"\n{'=' * 70}")
                print(f"✅ SUCCESS! CODE EXECUTED WITHOUT ERRORS!")
                print(f"{'=' * 70}")
                print(f"\n📊 Final output (last 50 lines):")
                print('\n'.join(output.split('\n')[-50:]))
                print(f"\n{'=' * 70}")
                sys.stdout.flush()
                return True, output
            
            # Extract error information
            print(f"\n🔍 Extracting error information...")
            error_info = self.extract_error_info(output)
            print(f"\n❌ EXECUTION FAILED")
            print(f"   Exit code: {return_code}")
            print(f"   Error detected around line: {error_info['error_line']}")
            error_type = error_info.get('error_type', 'Unknown') or 'Unknown'
            print(f"   Error type: {str(error_type)[:100]}")
            sys.stdout.flush()
            
            # Ask Claude for fix
            fix_suggestion = self.ask_claude_to_fix(code_file, error_info)
            
            if fix_suggestion is None:
                print(f"\n⚠️  COULD NOT GET FIX SUGGESTION FROM CLAUDE")
                print(f"   Skipping to next attempt...")
                sys.stdout.flush()
                continue
            
            # Try to automatically apply the fix
            fix_applied = self.parse_and_apply_fix(code_file, fix_suggestion)
            
            if fix_applied:
                print(f"\n✅ FIX APPLIED SUCCESSFULLY!")
                print(f"   Moving to next iteration to test the fix...")
                sys.stdout.flush()
            else:
                print(f"\n⚠️  COULD NOT APPLY FIX AUTOMATICALLY")
                print(f"   This pattern is not supported yet")
                print(f"   Full suggestion: {fix_suggestion[:500]}...")
                print(f"   Skipping to next attempt...")
                sys.stdout.flush()
                continue
        
        print(f"\n😞 Failed to fix code after {self.max_attempts} attempts")
        return False, output


def main():
    if len(sys.argv) < 2:
        print("Usage: python claude_code_cli_auto_fixer.py <code_file>")
        print("Example: python claude_code_cli_auto_fixer.py core/sandbox/exe_code/node_test_broken.py")
        sys.exit(1)
    
    code_file = sys.argv[1]
    
    if not os.path.exists(code_file):
        print(f"Error: File not found: {code_file}")
        sys.exit(1)
    
    fixer = ClaudeCodeCLIAutoFixer()
    success, final_output = fixer.auto_fix_and_run(code_file)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

