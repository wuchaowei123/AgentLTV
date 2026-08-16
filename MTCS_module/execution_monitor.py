#!/usr/bin/env python3
"""
Execution Monitor and Database Status Tool
=========================================

Monitor execution queue status, view results, and manage manual executions.
"""

import argparse
import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.database.db_manager import DatabaseManager


def display_queue_status(db: DatabaseManager):
    """Display current execution queue status."""
    stats = db.get_execution_statistics()
    
    print("🔄 EXECUTION QUEUE STATUS")
    print("=" * 50)
    print(f"📊 Total Nodes: {stats['total_nodes']}")
    print(f"✅ Success Rate: {stats['success_rate']:.1f}%")
    
    if stats['best_score']:
        print(f"🏆 Best Score: {stats['best_score']:.4f}")
    if stats['average_score']:
        print(f"📈 Average Score: {stats['average_score']:.4f}")
    
    print(f"\n📋 Status Breakdown:")
    status_counts = stats['status_counts']
    for status, count in status_counts.items():
        emoji = {
            'pending': '⏳',
            'executing': '🔄',
            'completed': '✅',
            'failed': '❌',
            'manual_required': '🚨'
        }.get(status, '❓')
        print(f"   {emoji} {status}: {count}")


def display_manual_required_nodes(db: DatabaseManager):
    """Display nodes requiring manual execution."""
    manual_nodes = db.get_manual_required_nodes()
    
    if not manual_nodes:
        print("✅ No nodes require manual execution")
        return
    
    print(f"\n🚨 NODES REQUIRING MANUAL EXECUTION ({len(manual_nodes)})")
    print("=" * 60)
    
    for node in manual_nodes:
        print(f"📁 Node: {node.node_id}")
        print(f"   File: {node.code_file_path}")
        print(f"   Error: {node.error_message}")
        print(f"   Mutation: {node.mutation_type}")
        print(f"   Generation: {node.generation}")
        print(f"   Created: {node.created_at}")
        print()
        
        # Show execution instructions
        print(f"   🔧 Manual Execution Instructions:")
        print(f"      1. cd /home/jupyter/scientific-ai-system")
        print(f"      2. conda activate trae-agent")
        print(f"      3. python {node.code_file_path}")
        print(f"      4. python manual_update_result.py --node-id {node.node_id} --score <score> --success")
        print("   " + "-" * 50)


def display_best_nodes(db: DatabaseManager, limit: int = 10):
    """Display best performing nodes."""
    best_nodes = db.get_best_nodes(limit)
    
    if not best_nodes:
        print("📊 No completed nodes found")
        return
    
    print(f"\n🏆 TOP {len(best_nodes)} PERFORMING NODES")
    print("=" * 60)
    
    for i, node in enumerate(best_nodes, 1):
        print(f"{i:2d}. Node: {node.node_id} | Score: {node.score:.4f}")
        print(f"     Mutation: {node.mutation_type} | Generation: {node.generation}")
        if node.execution_duration:
            print(f"     Runtime: {node.execution_duration:.1f}s | Auto-fixes: {node.auto_fixes}")
        print()


def display_failed_nodes(db: DatabaseManager, limit: int = 5):
    """Display recent failed nodes."""
    failed_nodes = db.get_failed_nodes()
    
    if not failed_nodes:
        print("✅ No failed nodes")
        return
    
    recent_failed = failed_nodes[-limit:]  # Get most recent
    
    print(f"\n❌ RECENT FAILED NODES ({len(recent_failed)})")
    print("=" * 60)
    
    for node in recent_failed:
        print(f"📁 Node: {node.node_id}")
        print(f"   Error: {node.error_message}")
        print(f"   Mutation: {node.mutation_type}")
        print(f"   Created: {node.created_at}")
        print()


def monitor_execution_queue(db: DatabaseManager, refresh_interval: int = 10):
    """Monitor execution queue with live updates."""
    print("🔍 LIVE EXECUTION MONITORING")
    print("=" * 50)
    print("Press Ctrl+C to stop monitoring")
    print()
    
    try:
        while True:
            # Clear screen
            print("\033[2J\033[H")
            
            # Display timestamp
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"⏰ Last Update: {current_time}")
            print()
            
            # Display status
            display_queue_status(db)
            
            # Show pending nodes
            pending_nodes = db.get_pending_nodes()
            if pending_nodes:
                print(f"\n⏳ PENDING EXECUTION ({len(pending_nodes)} nodes)")
                for node in pending_nodes[:3]:  # Show first 3
                    print(f"   - {node.node_id}: {node.mutation_type}")
                if len(pending_nodes) > 3:
                    print(f"   ... and {len(pending_nodes) - 3} more")
            
            # Show manual required nodes
            manual_nodes = db.get_manual_required_nodes()
            if manual_nodes:
                print(f"\n🚨 MANUAL EXECUTION REQUIRED ({len(manual_nodes)} nodes)")
                for node in manual_nodes:
                    print(f"   - {node.node_id}: {node.error_message}")
            
            print(f"\n🔄 Refreshing in {refresh_interval} seconds...")
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")


def export_results(db: DatabaseManager, output_file: str):
    """Export all results to CSV."""
    if db.export_results(output_file):
        print(f"✅ Results exported to: {output_file}")
    else:
        print(f"❌ Failed to export results")


def main():
    """Main function for execution monitoring."""
    parser = argparse.ArgumentParser(
        description="Monitor execution queue and manage database",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--db-path",
        type=str,
        default="execution_tracking.db",
        help="Path to database file (default: execution_tracking.db)"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current queue status"
    )
    
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Show nodes requiring manual execution"
    )
    
    parser.add_argument(
        "--best",
        type=int,
        metavar="N",
        help="Show top N performing nodes"
    )
    
    parser.add_argument(
        "--failed",
        type=int,
        metavar="N",
        help="Show N most recent failed nodes"
    )
    
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Start live monitoring"
    )
    
    parser.add_argument(
        "--refresh",
        type=int,
        default=10,
        help="Refresh interval for monitoring (seconds, default: 10)"
    )
    
    parser.add_argument(
        "--export",
        type=str,
        metavar="FILE",
        help="Export results to CSV file"
    )
    
    parser.add_argument(
        "--cleanup",
        type=int,
        metavar="DAYS",
        help="Remove nodes older than DAYS"
    )
    
    args = parser.parse_args()
    
    # Initialize database
    try:
        db = DatabaseManager(args.db_path)
        print(f"✅ Connected to database: {args.db_path}")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)
    
    # Execute requested actions
    if args.status:
        display_queue_status(db)
    
    if args.manual:
        display_manual_required_nodes(db)
    
    if args.best is not None:
        display_best_nodes(db, args.best)
    
    if args.failed is not None:
        display_failed_nodes(db, args.failed)
    
    if args.export:
        export_results(db, args.export)
    
    if args.cleanup is not None:
        removed = db.cleanup_old_nodes(args.cleanup)
        print(f"🧹 Removed {removed} old nodes")
    
    if args.monitor:
        monitor_execution_queue(db, args.refresh)
    
    # Default action: show status
    if not any([args.status, args.manual, args.best is not None, 
               args.failed is not None, args.export, args.cleanup, args.monitor]):
        display_queue_status(db)
        print()
        display_manual_required_nodes(db)


if __name__ == "__main__":
    main()