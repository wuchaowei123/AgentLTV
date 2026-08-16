#!/usr/bin/env python3
"""
Database-Enhanced Universal MTCS_module - Main Entry Point
==================================================================

Complete integration of the enhanced AI system with database-driven execution,
providing maximum reliability, persistence, and manual execution fallback.
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.task_manager import TaskConfiguration
from core.controller.db_enhanced_search import DatabaseEnhancedTreeSearch, DatabaseSearchConfiguration
from core.sandbox.db_universal_evaluator import DatabaseUniversalEvaluator


def parse_arguments():
    """Parse command line arguments for database-enhanced system."""
    parser = argparse.ArgumentParser(
        description="Database-Enhanced Universal AI System for Scientific Software Discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Database-Enhanced Features:
  - 100% execution tracking with SQLite database
  - Automatic manual execution fallback for failures
  - Persistent state across system restarts
  - Real-time monitoring and analytics
  - Zero-loss execution guarantee
  - Complete error tracking and debugging

Examples:
  # Quick database-enhanced test
  python universal_main_database.py --task tasks/kaggle_machine_failures/task_config.yaml --iterations 5
  
  # Full enhanced run with database tracking
  python universal_main_database.py --task tasks/kaggle_machine_failures/task_config.yaml --iterations 20 --enable-all-phases
  
  # Database-enhanced with manual execution support
  python universal_main_database.py --task tasks/kaggle_machine_failures/task_config.yaml --iterations 15 --wait-for-manual
  
  # Skip auto-fixer and go directly to manual execution
  python universal_main_database.py --task tasks/kaggle_machine_failures/task_config.yaml --iterations 10 --skip-auto-fixer
  
  # Resume previous search from database
  python universal_main_database.py --task tasks/kaggle_machine_failures/task_config.yaml --iterations 10 --db-path previous_search.db
        """
    )
    
    # Core arguments
    parser.add_argument(
        "--task", 
        type=str, 
        required=True,
        help="Path to task configuration YAML file"
    )
    
    parser.add_argument(
        "--iterations", 
        type=int, 
        default=20,
        help="Number of tree search iterations (default: 20)"
    )
    
    parser.add_argument(
        "--c-puct", 
        type=float, 
        default=1.5,
        help="PUCT exploration parameter (default: 1.5, used if adaptive disabled)"
    )
    
    # Adaptive C-PUCT options
    parser.add_argument(
        "--disable-adaptive-c-puct",
        action="store_true",
        help="Disable adaptive C-PUCT and use fixed value (default: adaptive enabled)"
    )
    
    parser.add_argument(
        "--c-puct-early",
        type=float,
        default=2.5,
        help="C-PUCT for early phase (0-20%%) when adaptive enabled (default: 2.5)"
    )
    
    parser.add_argument(
        "--c-puct-mid",
        type=float,
        default=1.5,
        help="C-PUCT for mid phase (20-70%%) when adaptive enabled (default: 1.5)"
    )
    
    parser.add_argument(
        "--c-puct-late",
        type=float,
        default=0.8,
        help="C-PUCT for late phase (70-100%%) when adaptive enabled (default: 0.8)"
    )
    
    # Database-specific features
    parser.add_argument(
        "--db-path",
        type=str,
        default="enhanced_search.db",
        help="Path to SQLite database file (default: enhanced_search.db)"
    )
    
    parser.add_argument(
        "--wait-for-manual",
        action="store_true",
        help="Wait for manual execution completion when automatic execution fails"
    )
    
    parser.add_argument(
        "--skip-auto-fixer",
        action="store_true",
        help="Skip auto-fixer entirely and go directly to manual execution for all nodes"
    )
    
    parser.add_argument(
        "--manual-timeout",
        type=int,
        default=300,
        help="Timeout for manual execution completion in seconds (default: 300)"
    )
    
    parser.add_argument(
        "--execution-timeout",
        type=int,
        default=600,
        help="Timeout for node code execution in seconds (default: 600)"
    )
    
    # User feedback system
    parser.add_argument(
        "--enable-user-feedback",
        action="store_true",
        help="Enable user feedback collection after successful executions"
    )
    
    parser.add_argument(
        "--feedback-timeout",
        type=int,
        default=30,
        help="Timeout for user feedback input in seconds (default: 30)"
    )
    
    # Code reload system
    parser.add_argument(
        "--enable-code-reload",
        action="store_true",
        help="Enable code reload after execution to detect manual edits"
    )
    
    parser.add_argument(
        "--reload-wait-time",
        type=int,
        default=60,
        help="Time to wait for manual code edits in seconds (default: 60)"
    )
    
    parser.add_argument(
        "--export-frequency",
        type=int,
        default=10,
        help="Export results every N iterations (default: 10)"
    )
    
    # Enhanced features
    parser.add_argument(
        "--enable-all-phases",
        action="store_true",
        help="Enable all phases: preparation, main search, and analysis"
    )
    
    parser.add_argument(
        "--research-enhanced",
        action="store_true", 
        help="Enable research idea brainstorming and integration"
    )
    
    parser.add_argument(
        "--multi-strategy-init",
        action="store_true",
        default=True,
        help="Use multiple initialization strategies (default: enabled)"
    )
    
    parser.add_argument(
        "--hybridization-frequency",
        type=int,
        default=10,
        help="Frequency of periodic hybridization (every N iterations, default: 10)"
    )
    
    # Monitoring and analytics
    parser.add_argument(
        "--enable-monitoring",
        action="store_true",
        default=True,
        help="Enable real-time execution monitoring (default: enabled)"
    )
    
    parser.add_argument(
        "--disable-monitoring",
        action="store_true",
        help="Disable real-time execution monitoring"
    )
    
    # Output and logging
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results_database",
        help="Directory to save results (default: results_database)"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable detailed logging"
    )
    
    # Database management
    parser.add_argument(
        "--cleanup-days",
        type=int,
        help="Clean up database entries older than N days before starting"
    )
    
    parser.add_argument(
        "--show-db-status",
        action="store_true",
        help="Show database status before starting search"
    )
    
    parser.add_argument(
        "--export-final-results",
        type=str,
        help="Export final results to specified CSV file"
    )
    
    return parser.parse_args()


def validate_database_environment():
    """Validate that database environment is properly set up."""
    print("🔍 Validating database environment...")
    
    # Check Google Cloud Project
    # Check Claude API configuration
    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("⚠️  Warning: ANTHROPIC_AUTH_TOKEN not set. Setting default...")
        os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-1gcvcMUA8g8aNy7y_FRfXg"
    
    if not os.environ.get("ANTHROPIC_BASE_URL"):
        print("ℹ️  Setting default ANTHROPIC_BASE_URL...")
        os.environ["ANTHROPIC_BASE_URL"] = "http://litellm.aviagames.net"
    
    print(f"✅ Claude API configured: {os.environ.get('ANTHROPIC_BASE_URL')}")
    
    # Check database directory permissions
    db_dir = Path(".")
    if not os.access(db_dir, os.W_OK):
        print(f"⚠️  Warning: No write permission in current directory for database")
        return False
    
    print("✅ Database environment validation passed")
    return True


def display_database_task_info(task_config: TaskConfiguration, args):
    """Display database-enhanced task information."""
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "Database-Enhanced Universal Scientific AI" + " " * 17 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    print(f"🎯 Domain: {task_config.domain}")
    print(f"📋 Task: {task_config.task_name}")
    print(f"📊 Metric: {task_config.evaluation_metric}")
    print(f"📁 Data Files: {list(task_config.data_files.keys())}")
    
    # Database features status
    print(f"\n🗄️ Database Features:")
    print(f"   • Database Path: {args.db_path}")
    print(f"   • Manual Execution: {'✅ (wait enabled)' if args.wait_for_manual else '⚠️ (auto-continue)'}")
    print(f"   • Monitoring: {'✅' if not args.disable_monitoring else '❌'}")
    print(f"   • User Feedback: {'✅' if args.enable_user_feedback else '❌'}")
    print(f"   • Code Reload: {'✅' if args.enable_code_reload else '❌'}")
    print(f"   • Export Frequency: Every {args.export_frequency} iterations")
    
    # Adaptive C-PUCT status
    print(f"\n🎯 Search Configuration:")
    if not args.disable_adaptive_c_puct:
        print(f"   • Adaptive C-PUCT: ✅ Enabled")
        print(f"     - Early phase (0-20%): C = {args.c_puct_early}")
        print(f"     - Mid phase (20-70%): C = {args.c_puct_mid}")
        print(f"     - Late phase (70-100%): C = {args.c_puct_late}")
    else:
        print(f"   • Adaptive C-PUCT: ❌ Disabled")
        print(f"   • Fixed C-PUCT: {args.c_puct}")
    
    # Enhanced features status
    print(f"\n🚀 Enhanced Features:")
    preparation_enabled = args.enable_all_phases or args.research_enhanced
    analysis_enabled = args.enable_all_phases or args.research_enhanced
    
    print(f"   • Phase 1 (Preparation): {'✅' if preparation_enabled else '❌'}")
    print(f"   • Phase 2 (Enhanced Search): ✅ (database-integrated)")
    print(f"   • Phase 3 (Analysis): {'✅' if analysis_enabled else '❌'}")
    print(f"   • Multi-strategy Init: {'✅' if args.multi_strategy_init else '❌'}")
    print(f"   • Research Integration: {'✅' if args.research_enhanced else '❌'}")
    
    if task_config.research_ideas:
        print(f"\n💡 Research Ideas:")
        for idea in task_config.research_ideas[:3]:  # Show first 3
            print(f"   • {idea}")
        if len(task_config.research_ideas) > 3:
            print(f"   • ... and {len(task_config.research_ideas) - 3} more")
    
    print(f"\n🔄 Starting database-enhanced automated scientific software discovery...")
    print("=" * 80)


def show_database_status(db_path: str):
    """Show current database status."""
    if not os.path.exists(db_path):
        print(f"📊 Database Status: New database will be created at {db_path}")
        return
    
    try:
        from core.database.db_manager import DatabaseManager
        db = DatabaseManager(db_path)
        stats = db.get_execution_statistics()
        
        print(f"📊 Existing Database Status ({db_path}):")
        print(f"   • Total Nodes: {stats['total_nodes']}")
        print(f"   • Success Rate: {stats['success_rate']:.1f}%")
        if stats['best_score']:
            print(f"   • Best Score: {stats['best_score']:.4f}")
        
        # Show status breakdown
        status_counts = stats['status_counts']
        for status, count in status_counts.items():
            emoji = {
                'pending': '⏳',
                'executing': '🔄',
                'completed': '✅',
                'failed': '❌',
                'manual_required': '🚨'
            }.get(status, '❓')
            print(f"   • {emoji} {status}: {count}")
        
        print()
        
    except Exception as e:
        print(f"⚠️ Could not read database status: {e}")


def run_database_enhanced_search(task_config: TaskConfiguration, args) -> dict:
    """Run the database-enhanced search system."""
    
    # Create database search configuration
    db_config = DatabaseSearchConfiguration(
        db_path=args.db_path,
        c_puct=args.c_puct,
        max_iterations=args.iterations,
        enable_preparation_phase=args.enable_all_phases or args.research_enhanced,
        enable_analysis_phase=args.enable_all_phases or args.research_enhanced,
        multi_strategy_initialization=args.multi_strategy_init,
        hybridization_frequency=args.hybridization_frequency,
        enable_monitoring=not args.disable_monitoring,
        wait_for_manual_completion=args.wait_for_manual,
        skip_auto_fixer=args.skip_auto_fixer,
        manual_execution_timeout=args.manual_timeout,
        execution_timeout=args.execution_timeout,
        export_results_frequency=args.export_frequency,
        enable_user_feedback=args.enable_user_feedback,
        user_feedback_timeout=args.feedback_timeout,
        enable_code_reload=args.enable_code_reload,
        code_reload_wait_time=args.reload_wait_time,
        # Adaptive C-PUCT settings
        use_adaptive_c_puct=not args.disable_adaptive_c_puct,
        c_puct_early=args.c_puct_early,
        c_puct_mid=args.c_puct_mid,
        c_puct_late=args.c_puct_late
    )
    
    # Create database-enhanced search agent
    search_agent = DatabaseEnhancedTreeSearch(
        task_config=task_config,
        db_config=db_config
    )
    
    # Run database-enhanced search
    best_solution = search_agent.run_database_enhanced_search(args.iterations)
    
    # Get comprehensive results
    results = search_agent.get_database_search_results()
    
    return {
        'best_solution': best_solution,
        'search_agent': search_agent,
        'results': results,
        'config': db_config
    }


def save_database_enhanced_results(results: dict, output_dir: Path, args):
    """Save comprehensive results from database-enhanced system."""
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save best solution
    best_solution = results['best_solution']
    best_code_file = output_dir / "best_database_solution.py"
    with open(best_code_file, 'w') as f:
        f.write(f"# Database-Enhanced Universal AI System - Best Solution\n")
        f.write(f"# Task: {results['results']['task_info']['task_name']}\n")
        f.write(f"# {results['results']['task_info']['evaluation_metric']}: {best_solution.score:.6f}\n")
        f.write(f"# Strategy: {best_solution.genealogy.mutation_type}\n")
        f.write(f"# Database Node: {getattr(best_solution, 'node_id', 'Unknown')}\n")
        if best_solution.genealogy.research_ideas_used:
            f.write(f"# Research Ideas: {', '.join(best_solution.genealogy.research_ideas_used[:3])}\n")
        f.write(f"\n{best_solution.code}")
    
    # Save comprehensive results summary
    summary_file = output_dir / "database_enhanced_results.txt"
    with open(summary_file, 'w') as f:
        f.write("Database-Enhanced Universal MTCS_module - Results\n")
        f.write("=" * 60 + "\n\n")
        
        # Database-enhanced results
        db_stats = results['results']['database_enhanced_stats']
        eval_stats = results['results']['database_evaluation_stats']
        
        f.write(f"🏆 DATABASE-ENHANCED RESULTS:\n")
        f.write(f"   Best Score: {best_solution.score:.6f}\n")
        f.write(f"   Strategy: {best_solution.genealogy.mutation_type}\n")
        f.write(f"   Database Node: {getattr(best_solution, 'node_id', 'Unknown')}\n")
        f.write(f"   Generation: {best_solution.genealogy.generation}\n\n")
        
        f.write(f"🗄️ DATABASE INTEGRATION:\n")
        f.write(f"   Database Path: {db_stats['database_path']}\n")
        f.write(f"   Success Rate: {eval_stats['success_rate']:.1f}%\n")
        f.write(f"   Manual Executions Completed: {db_stats['manual_executions_completed']}\n")
        f.write(f"   Manual Executions Pending: {db_stats['manual_executions_pending']}\n")
        f.write(f"   Total Auto-fixes: {db_stats['total_auto_fixes']}\n")
        f.write(f"   Database Exports: {db_stats['database_exports_created']}\n\n")
        
        f.write(f"📊 EVALUATION STATISTICS:\n")
        eval_stats_detail = eval_stats['evaluation_stats']
        f.write(f"   Total Evaluations: {eval_stats_detail['total_evaluations']}\n")
        f.write(f"   Successful: {eval_stats_detail['successful_evaluations']}\n")
        f.write(f"   Failed: {eval_stats_detail['failed_evaluations']}\n")
        f.write(f"   Manual Required: {eval_stats_detail['manual_executions_required']}\n")
        f.write(f"   Auto-fixes Applied: {eval_stats_detail['auto_fixes_applied']}\n\n")
        
        f.write(f"🎯 TOP DATABASE NODES:\n")
        for i, node_info in enumerate(results['results']['best_nodes_from_database'], 1):
            f.write(f"   {i}. {node_info['node_id']}: {node_info['score']:.4f} ({node_info['mutation_type']})\n")
    
    return best_code_file


def main():
    """Main execution function for database-enhanced system."""
    args = parse_arguments()
    
    # Validate environment
    if not validate_database_environment():
        print("❌ Environment validation failed. Some features may not work.")
    
    # Load task configuration
    try:
        task_config = TaskConfiguration(args.task)
    except Exception as e:
        print(f"❌ Error loading task configuration: {e}")
        sys.exit(1)
    
    # Show database status if requested
    if args.show_db_status:
        show_database_status(args.db_path)
    
    # Clean up old database entries if requested
    if args.cleanup_days:
        try:
            from core.database.db_manager import DatabaseManager
            db = DatabaseManager(args.db_path)
            removed = db.cleanup_old_nodes(args.cleanup_days)
            print(f"🧹 Cleaned up {removed} database entries older than {args.cleanup_days} days")
        except Exception as e:
            print(f"⚠️ Database cleanup failed: {e}")
    
    # Display database-enhanced task information
    display_database_task_info(task_config, args)

    # Create output directory
    output_dir = Path(args.output_dir) / f"db_enhanced_{task_config.domain}_{task_config.task_name.replace(' ', '_')}"
    
    try:
        # Run database-enhanced search
        results = run_database_enhanced_search(task_config, args)
        
        # Display final results
        best_solution = results['best_solution']
        db_stats = results['results']['database_enhanced_stats']
        eval_stats = results['results']['database_evaluation_stats']
        
        print("\n" + "=" * 80)
        print("🎉 Database-Enhanced Scientific Software Discovery Complete!")
        print("=" * 80)
        print(f"🏆 Best Score: {best_solution.score:.6f}")
        print(f"🔬 Strategy Used: {best_solution.genealogy.mutation_type}")
        print(f"🗄️ Database Node: {getattr(best_solution, 'node_id', 'Unknown')}")
        print(f"📊 Total Nodes Explored: {len(results['search_agent'].nodes)}")
        print(f"✅ Database Success Rate: {eval_stats['success_rate']:.1f}%")
        print(f"🔧 Manual Executions: {db_stats['manual_executions_completed']}")
        print(f"🛠️ Auto-fixes Applied: {db_stats['total_auto_fixes']}")
        
        # Save results
        best_code_file = save_database_enhanced_results(results, output_dir, args)
        print(f"\n💾 Results saved to: {output_dir}")
        print(f"💡 Best solution saved to: {best_code_file}")
        print(f"🗄️ Database available at: {args.db_path}")
        
        # Export final results if requested
        if args.export_final_results:
            search_agent = results['search_agent']
            if search_agent.db_evaluator.export_results(args.export_final_results):
                print(f"📊 Final results exported to: {args.export_final_results}")
        
        # Show database monitoring commands
        print(f"\n🔍 Monitor database with:")
        print(f"   python execution_monitor.py --db-path {args.db_path} --status")
        print(f"   python execution_monitor.py --db-path {args.db_path} --best 10")
        print(f"   python execution_monitor.py --db-path {args.db_path} --manual")
        
        # Show best code if verbose
        if args.verbose:
            print(f"\n📝 Best Database-Enhanced Solution Code:")
            print("-" * 60)
            print(best_solution.code[:500] + "..." if len(best_solution.code) > 500 else best_solution.code)
        
    except KeyboardInterrupt:
        print("\n⚠️  Search interrupted by user")
        print(f"💾 Progress saved in database: {args.db_path}")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error during database-enhanced search: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        print(f"💾 Partial progress may be saved in database: {args.db_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()