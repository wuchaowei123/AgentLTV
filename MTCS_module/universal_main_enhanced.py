#!/usr/bin/env python3
"""
Enhanced Universal MTCS_module - Main Entry Point
=========================================================

Enhanced version implementing the complete AI system graph workflow with:
- Phase 1: Research preparation and multi-strategy initialization
- Phase 2: Intelligent tree search with advisory prompts
- Phase 3: Solution analysis and hybridization

Based on the complete AI system graph and prompt library.
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
from core.controller.enhanced_search import EnhancedUniversalTreeSearch, EnhancedSearchConfiguration
from core.sandbox.universal_evaluator import UniversalCodeEvaluator


def parse_arguments():
    """Parse command line arguments for enhanced system."""
    parser = argparse.ArgumentParser(
        description="Enhanced Universal AI System for Scientific Software Discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Enhanced Features:
  - Multi-phase architecture (preparation, main search, analysis)
  - Research idea brainstorming and integration
  - Multiple initialization strategies
  - Intelligent prompt strategy selection
  - Solution analysis and hybridization
  - Advisory prompt integration

Examples:
  # Quick enhanced test
  python universal_main_enhanced.py --task tasks/kaggle_machine_failures/task_config.yaml --iterations 5
  
  # Full enhanced run with all phases
  python universal_main_enhanced.py --task tasks/kaggle_machine_failures/task_config.yaml --iterations 20 --enable-all-phases
  
  # Research-focused run
  python universal_main_enhanced.py --task tasks/kaggle_machine_failures/task_config.yaml --iterations 15 --research-enhanced
  
  # Multi-strategy initialization only
  python universal_main_enhanced.py --task tasks/kaggle_machine_failures/task_config.yaml --iterations 10 --multi-strategy-only
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
        help="PUCT exploration parameter (default: 1.5)"
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
        "--disable-preparation",
        action="store_true",
        help="Disable Phase 1 preparation (use standard initialization)"
    )
    
    parser.add_argument(
        "--disable-analysis", 
        action="store_true",
        help="Disable Phase 3 solution analysis and hybridization"
    )
    
    parser.add_argument(
        "--hybridization-frequency",
        type=int,
        default=10,
        help="Frequency of periodic hybridization (every N iterations, default: 10)"
    )
    
    parser.add_argument(
        "--max-strategies",
        type=int,
        default=4,
        help="Maximum number of initialization strategies (default: 4)"
    )
    
    # Output and logging
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results_enhanced",
        help="Directory to save results (default: results_enhanced)"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable detailed logging"
    )
    
    parser.add_argument(
        "--save-all-solutions",
        action="store_true",
        help="Save all candidate solutions, not just the best"
    )
    
    # Backwards compatibility options
    parser.add_argument(
        "--standard-mode",
        action="store_true",
        help="Run in standard mode (disable all enhancements)"
    )
    
    parser.add_argument(
        "--compare-with-baseline",
        action="store_true",
        help="Run both enhanced and baseline systems for comparison"
    )
    
    return parser.parse_args()


def validate_environment():
    """Validate that all required environments and dependencies are available."""
    print("🔍 Validating environment...")
    
    # Check Claude API configuration
    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("⚠️  Warning: ANTHROPIC_AUTH_TOKEN not set. Setting default...")
        os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-1gcvcMUA8g8aNy7y_FRfXg"
    
    if not os.environ.get("ANTHROPIC_BASE_URL"):
        print("ℹ️  Setting default ANTHROPIC_BASE_URL...")
        os.environ["ANTHROPIC_BASE_URL"] = "http://litellm.aviagames.net"
    
    print(f"✅ Claude API configured: {os.environ.get('ANTHROPIC_BASE_URL')}")
    print("✅ Environment validation passed")
    return True


def display_enhanced_task_info(task_config: TaskConfiguration, args):
    """Display enhanced task information."""
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "Enhanced Universal MTCS_module" + " " * 14 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    print(f"🎯 Domain: {task_config.domain}")
    print(f"📋 Task: {task_config.task_name}")
    print(f"📊 Metric: {task_config.evaluation_metric}")
    print(f"📁 Data Files: {list(task_config.data_files.keys())}")
    
    # Enhanced features status
    print(f"\n🚀 Enhanced Features:")
    preparation_enabled = not args.disable_preparation and (args.enable_all_phases or args.research_enhanced)
    analysis_enabled = not args.disable_analysis and (args.enable_all_phases or args.research_enhanced)
    
    print(f"   • Phase 1 (Preparation): {'✅' if preparation_enabled else '❌'}")
    print(f"   • Phase 2 (Enhanced Search): ✅")
    print(f"   • Phase 3 (Analysis): {'✅' if analysis_enabled else '❌'}")
    print(f"   • Multi-strategy Init: {'✅' if args.multi_strategy_init else '❌'}")
    print(f"   • Research Integration: {'✅' if args.research_enhanced else '❌'}")
    
    if task_config.research_ideas:
        print(f"\n💡 Research Ideas:")
        for idea in task_config.research_ideas[:3]:  # Show first 3
            print(f"   • {idea}")
        if len(task_config.research_ideas) > 3:
            print(f"   • ... and {len(task_config.research_ideas) - 3} more")
    
    print(f"\n🔄 Starting enhanced automated scientific software discovery...")
    print("=" * 70)


def run_enhanced_search(task_config: TaskConfiguration, args) -> dict:
    """Run the enhanced search system."""
    
    # Create enhanced search configuration
    enhanced_config = EnhancedSearchConfiguration(
        c_puct=args.c_puct,
        max_iterations=args.iterations,
        enable_preparation_phase=not args.disable_preparation and (args.enable_all_phases or args.research_enhanced),
        enable_analysis_phase=not args.disable_analysis and (args.enable_all_phases or args.research_enhanced),
        multi_strategy_initialization=args.multi_strategy_init and not args.standard_mode,
        max_preparation_strategies=args.max_strategies,
        hybridization_frequency=args.hybridization_frequency,
        min_solutions_for_analysis=3
    )
    
    # Create evaluator
    evaluator = UniversalCodeEvaluator(task_config)
    
    # Create enhanced search agent
    search_agent = EnhancedUniversalTreeSearch(
        task_config=task_config,
        evaluator=evaluator.evaluate,
        enhanced_config=enhanced_config
    )
    
    # Run enhanced search
    best_solution = search_agent.run_enhanced_search(args.iterations)
    
    # Get comprehensive results
    results = search_agent.get_enhanced_results()
    
    return {
        'best_solution': best_solution,
        'search_agent': search_agent,
        'results': results,
        'config': enhanced_config
    }


def run_baseline_comparison(task_config: TaskConfiguration, args) -> dict:
    """Run baseline system for comparison."""
    print("\n🔄 Running baseline system for comparison...")
    
    # Import baseline system
    from core.controller.search import UniversalTreeSearch, SearchConfiguration
    from core.llm_worker import UniversalLLMWorker
    
    # Create baseline configuration
    baseline_config = SearchConfiguration(
        c_puct=args.c_puct,
        max_iterations=args.iterations
    )
    
    # Create baseline components
    evaluator = UniversalCodeEvaluator(task_config)
    llm_worker = UniversalLLMWorker()
    
    # Create baseline search
    baseline_search = UniversalTreeSearch(
        task_config=task_config,
        evaluator=evaluator.evaluate,
        llm_worker=llm_worker,
        search_config=baseline_config
    )
    
    # Run baseline search
    baseline_best = baseline_search.run(args.iterations)
    baseline_results = baseline_search.get_search_results()
    
    return {
        'best_solution': baseline_best,
        'search_agent': baseline_search,
        'results': baseline_results
    }


def save_enhanced_results(enhanced_results: dict, baseline_results: dict, output_dir: Path, args):
    """Save comprehensive results from enhanced system."""
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save best enhanced solution
    best_enhanced = enhanced_results['best_solution']
    enhanced_code_file = output_dir / "best_enhanced_solution.py"
    with open(enhanced_code_file, 'w') as f:
        f.write(f"# Enhanced Universal AI System - Best Solution\n")
        f.write(f"# Task: {enhanced_results['results']['task_info']['task_name']}\n")
        f.write(f"# {enhanced_results['results']['task_info']['evaluation_metric']}: {best_enhanced.score:.6f}\n")
        f.write(f"# Strategy: {best_enhanced.genealogy.mutation_type}\n")
        if best_enhanced.genealogy.research_ideas_used:
            f.write(f"# Research Ideas: {', '.join(best_enhanced.genealogy.research_ideas_used[:3])}\n")
        f.write(f"\n{best_enhanced.code}")
    
    # Save comparison if baseline was run
    if baseline_results:
        best_baseline = baseline_results['best_solution']
        baseline_code_file = output_dir / "best_baseline_solution.py"
        with open(baseline_code_file, 'w') as f:
            f.write(f"# Baseline Universal AI System - Best Solution\n")
            f.write(f"# {baseline_results['results']['task_info']['evaluation_metric']}: {best_baseline.score:.6f}\n")
            f.write(f"\n{best_baseline.code}")
    
    # Save candidate solutions if requested
    if args.save_all_solutions:
        candidates_dir = output_dir / "candidate_solutions"
        candidates_dir.mkdir(exist_ok=True)
        
        search_agent = enhanced_results['search_agent']
        for i, (code, score) in enumerate(search_agent.candidate_solutions[:10]):  # Top 10
            candidate_file = candidates_dir / f"candidate_{i+1}_score_{score:.4f}.py"
            with open(candidate_file, 'w') as f:
                f.write(f"# Candidate Solution {i+1}\n")
                f.write(f"# Score: {score:.6f}\n")
                f.write(f"\n{code}")
    
    # Save comprehensive results summary
    summary_file = output_dir / "enhanced_results_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("Enhanced Universal MTCS_module - Results Summary\n")
        f.write("=" * 60 + "\n\n")
        
        # Enhanced results
        enhanced_stats = enhanced_results['results']['enhanced_stats']
        multi_phase = enhanced_results['results']['multi_phase_results']
        
        f.write(f"🏆 ENHANCED SYSTEM RESULTS:\n")
        f.write(f"   Best Score: {best_enhanced.score:.6f}\n")
        f.write(f"   Strategy: {best_enhanced.genealogy.mutation_type}\n")
        f.write(f"   Generation: {best_enhanced.genealogy.generation}\n\n")
        
        f.write(f"📊 MULTI-PHASE STATISTICS:\n")
        f.write(f"   Preparation Time: {enhanced_stats['preparation_phase_time']:.1f}s\n")
        f.write(f"   Analysis Time: {enhanced_stats['analysis_phase_time']:.1f}s\n")
        f.write(f"   Research Ideas Generated: {enhanced_stats['research_ideas_generated']}\n")
        f.write(f"   Hybrid Solutions Created: {enhanced_stats['hybrid_solutions_created']}\n")
        f.write(f"   Initialization Strategies: {len(multi_phase['initialization_strategies'])}\n\n")
        
        f.write(f"🎯 STRATEGY PERFORMANCE:\n")
        for strategy, count in enhanced_stats['strategies_attempted'].items():
            f.write(f"   {strategy}: {count} attempts\n")
        
        # Baseline comparison if available
        if baseline_results:
            best_baseline = baseline_results['best_solution']
            improvement = best_enhanced.score - best_baseline.score
            relative_improvement = (improvement / best_baseline.score) * 100 if best_baseline.score > 0 else 0
            
            f.write(f"\n🔄 BASELINE COMPARISON:\n")
            f.write(f"   Enhanced Score: {best_enhanced.score:.6f}\n")
            f.write(f"   Baseline Score: {best_baseline.score:.6f}\n")
            f.write(f"   Improvement: +{improvement:.6f} (+{relative_improvement:.1f}%)\n")
    
    return enhanced_code_file


def main():
    """Main execution function for enhanced system."""
    args = parse_arguments()
    
    # Validate environment
    if not validate_environment():
        print("❌ Environment validation failed. Some features may not work.")
    
    # Load task configuration
    try:
        task_config = TaskConfiguration(args.task)
    except Exception as e:
        print(f"❌ Error loading task configuration: {e}")
        sys.exit(1)
    
    # Display enhanced task information
    display_enhanced_task_info(task_config, args)
    
    # Create output directory
    output_dir = Path(args.output_dir) / f"enhanced_{task_config.domain}_{task_config.task_name.replace(' ', '_')}"
    
    try:
        # Run enhanced search
        enhanced_results = run_enhanced_search(task_config, args)
        
        # Run baseline comparison if requested
        baseline_results = None
        if args.compare_with_baseline:
            baseline_results = run_baseline_comparison(task_config, args)
        
        # Display final results
        best_enhanced = enhanced_results['best_solution']
        enhanced_stats = enhanced_results['results']['enhanced_stats']
        
        print("\n" + "=" * 70)
        print("🎉 Enhanced Scientific Software Discovery Complete!")
        print("=" * 70)
        print(f"🏆 Best Enhanced Score: {best_enhanced.score:.6f}")
        print(f"🔬 Strategy Used: {best_enhanced.genealogy.mutation_type}")
        print(f"📊 Total Nodes Explored: {len(enhanced_results['search_agent'].nodes)}")
        print(f"🧪 Research Ideas Generated: {enhanced_stats['research_ideas_generated']}")
        print(f"🧬 Hybrid Solutions Created: {enhanced_stats['hybrid_solutions_created']}")
        
        # Show comparison if available
        if baseline_results:
            best_baseline = baseline_results['best_solution']
            improvement = best_enhanced.score - best_baseline.score
            relative_improvement = (improvement / best_baseline.score) * 100 if best_baseline.score > 0 else 0
            
            print(f"\n🔄 ENHANCED vs BASELINE:")
            print(f"   Enhanced: {best_enhanced.score:.6f}")
            print(f"   Baseline: {best_baseline.score:.6f}")
            print(f"   Improvement: +{improvement:.6f} (+{relative_improvement:.1f}%)")
        
        # Save results
        best_code_file = save_enhanced_results(enhanced_results, baseline_results, output_dir, args)
        print(f"\n💾 Results saved to: {output_dir}")
        print(f"💡 Best enhanced code saved to: {best_code_file}")
        
        # Show best code if verbose
        if args.verbose:
            print(f"\n📝 Best Enhanced Solution Code:")
            print("-" * 50)
            print(best_enhanced.code[:500] + "..." if len(best_enhanced.code) > 500 else best_enhanced.code)
        
    except KeyboardInterrupt:
        print("\n⚠️  Search interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error during enhanced search: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()