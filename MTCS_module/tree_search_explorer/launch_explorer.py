#!/usr/bin/env python3
"""
Tree Search Explorer Launcher
============================

Simple launcher script for the Tree Search Explorer with automatic setup.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def find_database_files():
    """Find available database files in the parent directory."""
    parent_dir = Path(__file__).parent.parent
    db_files = list(parent_dir.glob("*.db"))
    return db_files

def launch_explorer(db_path=None, port=5000, host="0.0.0.0"):
    """Launch the Tree Search Explorer."""
    
    print("🌳 Tree Search Explorer Launcher")
    print("=" * 50)
    
    # Find database files if none specified
    if not db_path:
        db_files = find_database_files()
        if not db_files:
            print("❌ No database files found in parent directory")
            return False
        
        print(f"📊 Found {len(db_files)} database files:")
        for i, db_file in enumerate(db_files, 1):
            file_size = db_file.stat().st_size / 1024  # KB
            print(f"   {i}. {db_file.name} ({file_size:.1f} KB)")
        
        # Use the most recently modified database
        db_path = max(db_files, key=lambda p: p.stat().st_mtime)
        print(f"✅ Auto-selected: {db_path.name}")
    
    # Verify database exists
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        return False
    
    # Test data extraction first
    print("🔍 Testing data extraction...")
    try:
        cmd = [sys.executable, "data_bridge.py", str(db_path), "--pretty"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Data extraction successful")
            
            # Extract summary info from output
            for line in result.stdout.split('\n'):
                if 'Total Nodes:' in line or 'Best Score:' in line or 'Breakthrough Points:' in line:
                    print(f"   {line.strip()}")
        else:
            print(f"❌ Data extraction failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Data extraction timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing data extraction: {e}")
        return False
    
    # Start the Flask application
    print(f"\n🚀 Starting Tree Search Explorer...")
    print(f"   📊 Database: {Path(db_path).name}")
    print(f"   🌐 URL: http://{host}:{port}")
    print(f"   🛑 Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        cmd = [
            sys.executable, "app.py",
            "--db", str(db_path),
            "--port", str(port),
            "--host", host,
            "--debug"
        ]
        
        # Run the Flask app
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n🛑 Tree Search Explorer stopped")
        return True
    except Exception as e:
        print(f"❌ Error starting Flask app: {e}")
        return False

def main():
    """Main launcher function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Launch Tree Search Explorer")
    parser.add_argument("--db", help="Database file path")
    parser.add_argument("--port", type=int, default=5000, help="Port to run on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--list-dbs", action="store_true", help="List available databases and exit")
    
    args = parser.parse_args()
    
    if args.list_dbs:
        db_files = find_database_files()
        print("📊 Available Database Files:")
        if not db_files:
            print("   No database files found")
        else:
            for i, db_file in enumerate(db_files, 1):
                file_size = db_file.stat().st_size / 1024  # KB
                mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(db_file.stat().st_mtime))
                print(f"   {i}. {db_file.name} ({file_size:.1f} KB, modified: {mtime})")
        return
    
    success = launch_explorer(args.db, args.port, args.host)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()