#!/usr/bin/env python3
"""
Manual Execution Result Update Script
===================================

Allows manual updating of execution results when automatic execution fails.
"""

import argparse
import sys
import warnings
from pathlib import Path

# Suppress asyncio warnings for subprocess cleanup in Python 3.12+
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*Event loop is closed.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited.*")
warnings.filterwarnings("ignore", message=".*BaseSubprocessTransport.*")

# Also suppress the specific asyncio subprocess transport warnings
import os
os.environ.setdefault('PYTHONWARNINGS', 'ignore::RuntimeWarning')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.database.db_manager import DatabaseManager
from core.utils.error_cleaner import format_error_for_display


def main():
    """Main function for manual result updates."""
    parser = argparse.ArgumentParser(
        description="Manually update execution results for nodes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update successful execution result
  python manual_update_result.py --node-id abc123 --score 0.85 --success
  
  # Update successful result with corrected code
  python manual_update_result.py --node-id abc123 --score 0.85 --success --code-file fixed_code.py
  
  # Update failed execution result
  python manual_update_result.py --node-id def456 --error "ImportError: missing library"
  
  # Update with secondary scores
  python manual_update_result.py --node-id ghi789 --score 0.75 --secondary '{"f1": 0.73, "precision": 0.78}'
        """
    )
    
    parser.add_argument(
        "--node-id",
        type=str,
        required=True,
        help="ID of the node to update"
    )
    
    parser.add_argument(
        "--score",
        type=float,
        help="Primary score achieved (required for success)"
    )
    
    parser.add_argument(
        "--success",
        action="store_true",
        help="Mark execution as successful"
    )
    
    parser.add_argument(
        "--error",
        type=str,
        help="Error message for failed execution"
    )
    
    parser.add_argument(
        "--secondary",
        type=str,
        help="Secondary scores as JSON string"
    )
    
    parser.add_argument(
        "--auto-fixes",
        type=int,
        default=0,
        help="Number of automatic fixes applied (default: 0)"
    )
    
    parser.add_argument(
        "--code-file",
        type=str,
        help="Path to file containing updated code for this node"
    )
    
    parser.add_argument(
        "--code",
        type=str,
        help="Updated code content as string (alternative to --code-file)"
    )
    
    parser.add_argument(
        "--db-path",
        type=str,
        default="enhanced_search.db",
        help="Path to database file (default: enhanced_search.db)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.success and not args.score:
        print("❌ Error: --score is required when --success is specified")
        sys.exit(1)
    
    if not args.success and not args.error:
        print("❌ Error: Either --success or --error must be specified")
        sys.exit(1)
    
    # Handle code update if provided
    updated_code = None
    if args.code_file:
        try:
            from pathlib import Path
            code_path = Path(args.code_file)
            if not code_path.exists():
                print(f"❌ Error: Code file not found: {args.code_file}")
                sys.exit(1)
            updated_code = code_path.read_text(encoding='utf-8')
            print(f"📄 Loaded updated code from: {args.code_file}")
        except Exception as e:
            print(f"❌ Error reading code file: {e}")
            sys.exit(1)
    elif args.code:
        updated_code = args.code
        print(f"📄 Using provided code string")
    
    # Initialize database
    try:
        db = DatabaseManager(args.db_path)
        print(f"✅ Connected to database: {args.db_path}")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)
    
    # Check if node exists
    node = db.get_node(args.node_id)
    if not node:
        print(f"❌ Node not found: {args.node_id}")
        sys.exit(1)
    
    print(f"📋 Node: {args.node_id}")
    print(f"   Status: {node.execution_status}")
    print(f"   Mutation: {node.mutation_type}")
    print(f"   Generation: {node.generation}")
    
    # Update code if provided
    if updated_code:
        print(f"🔄 Updating code for node {args.node_id}...")
        code_updates = {'code': updated_code}
        code_success = db.update_node(args.node_id, code_updates)
        if code_success:
            print(f"✅ Successfully updated code for node {args.node_id}")
        else:
            print(f"❌ Failed to update code for node {args.node_id}")
            sys.exit(1)

    # Update result
    try:
        if args.success:
            # Parse secondary scores if provided
            secondary_scores = None
            if args.secondary:
                import json
                try:
                    secondary_scores = json.loads(args.secondary)
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON in --secondary: {e}")
                    sys.exit(1)
            
            # Update successful result
            success = db.update_execution_result(
                args.node_id,
                args.score,
                secondary_scores,
                None,  # predictions not provided in manual update
                args.auto_fixes
            )
            
            if success:
                print(f"✅ Successfully updated node {args.node_id}")
                print(f"   Score: {args.score}")
                if secondary_scores:
                    print(f"   Secondary scores: {secondary_scores}")
                print(f"   Auto-fixes: {args.auto_fixes}")
                if updated_code:
                    print(f"   Code: ✅ Updated")
            else:
                print(f"❌ Failed to update node {args.node_id}")
                sys.exit(1)
                
        else:
            # Update failed result
            success = db.update_execution_status(
                args.node_id,
                'failed',
                args.error
            )
            
            if success:
                print(f"✅ Marked node {args.node_id} as failed")
                print(f"   Error: {args.error}")
            else:
                print(f"❌ Failed to update node {args.node_id}")
                sys.exit(1)
        
        # Show updated statistics
        stats = db.get_execution_statistics()
        print(f"\n📊 Execution Statistics:")
        print(f"   Total nodes: {stats['total_nodes']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        if stats['best_score']:
            print(f"   Best score: {stats['best_score']:.4f}")
        
        # Check for pending manual executions
        manual_nodes = db.get_manual_required_nodes()
        if manual_nodes:
            print(f"\n⚠️ {len(manual_nodes)} nodes still require manual execution:")
            for node in manual_nodes[:3]:  # Show first 3
                # Clean up error messages for display using utility function
                error_msg = format_error_for_display(node.error_message, max_length=80)
                print(f"   - {node.node_id}: {error_msg}")
            if len(manual_nodes) > 3:
                print(f"   ... and {len(manual_nodes) - 3} more")
        
    except Exception as e:
        print(f"❌ Error updating result: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()