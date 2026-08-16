#!/usr/bin/env python3
"""
Universal Scientific AI System - Main Entry Point
================================================

A general-purpose AI system for automated scientific software discovery.
Uses LLM + Tree Search to generate expert-level code for any scorable task.

Usage:
    python main.py --task tasks/kaggle_machine_failures/task_config.yaml
    python main.py --task tasks/genomics_scrna/task_config.yaml --iterations 50
    python main.py --task tasks/climate_forecasting/task_config.yaml --research-ideas "Use physics-informed neural networks"
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
from core.controller.search import UniversalTreeSearch
from core.llm_worker import generate_code_mutation
from core.sandbox.universal_evaluator import UniversalCodeEvaluator

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Universal AI System for Scientific Software Discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Binary classification (demo)
  python main.py --task tasks/kaggle_machine_failures/task_config.yaml
  
  # Bioinformatics 
  python main.py --task tasks/genomics_scrna/task_config.yaml --iterations 30
  
  # Climate science
  python main.py --task tasks/climate_forecasting/task_config.yaml
  
  # Custom research ideas
  python main.py --task tasks/my_domain/task_config.yaml \\
      --research-ideas "Use graph neural networks" "Apply attention mechanisms"
        """
    )
    
    parser.add_argument(
        "--task", "-t",
        type=str,
        required=True,
        help="Path to task configuration YAML file"
    )
    
    parser.add_argument(
        "--iterations", "-i", 
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
    
    parser.add_argument(
        "--research-ideas",
        nargs="*",
        help="Additional research ideas to inject"
    )
    
    parser.add_argument(
        "--deep-research",
        type=str,
        help="Topic for automated deep research via Gemini"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Directory to save results (default: results)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of parallel evaluations (default: 1)"
    )
    
    return parser.parse_args()

def validate_environment():
    """Validate that required environment variables are set."""
    required_vars = ["GOOGLE_CLOUD_PROJECT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables:")
        print("   export GOOGLE_CLOUD_PROJECT='your-project-id'")
        return False
    
    # Check Claude API configuration
    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("ℹ️  Setting default ANTHROPIC_AUTH_TOKEN...")
        os.environ["ANTHROPIC_AUTH_TOKEN"] = "sk-1gcvcMUA8g8aNy7y_FRfXg"
    
    if not os.environ.get("ANTHROPIC_BASE_URL"):
        print("ℹ️  Setting default ANTHROPIC_BASE_URL...")
        os.environ["ANTHROPIC_BASE_URL"] = "http://litellm.aviagames.net"
    
    print(f"✅ Claude API configured: {os.environ.get('ANTHROPIC_BASE_URL')}")
        
    return True

def display_task_info(task_config: TaskConfiguration):
    """Display information about the loaded task."""
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                     Universal Scientific AI System                ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()
    print(f"🎯 Domain: {task_config.domain}")
    print(f"📋 Task: {task_config.task_name}")
    print(f"📊 Metric: {task_config.evaluation_metric}")
    print(f"📁 Data Files: {list(task_config.data_files.keys())}")
    
    if task_config.research_ideas:
        print(f"💡 Research Ideas:")
        for idea in task_config.research_ideas:
            print(f"   • {idea}")
    
    print()
    print("🔄 Starting automated scientific software discovery...")
    print("=" * 70)

def create_initial_prompt(task_config: TaskConfiguration) -> str:
    """Create initial prompt for the root node based on task configuration."""
    
    domain_templates = {
        "machine_learning": """
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

# Load data
train_df = pd.read_csv('{train_file}')
val_df = pd.read_csv('{val_file}')

# Prepare features and target
feature_cols = [col for col in train_df.columns if col not in ['{target_col}', 'Product ID', 'UDI']]
X_train = train_df[feature_cols]
y_train = train_df['{target_col}']
X_val = val_df[feature_cols]
y_val = val_df['{target_col}']

# Basic preprocessing
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)

# Simple baseline model
model = LogisticRegression(random_state=42)
model.fit(X_train_scaled, y_train)

# Generate predictions
val_predictions = model.predict_proba(X_val_scaled)[:, 1]
""",
        
        "bioinformatics": """
import scanpy as sc
import pandas as pd
import numpy as np
from sklearn.metrics import silhouette_score

# Load single-cell data
adata = sc.read_h5ad('{expression_matrix}')
batch_info = pd.read_csv('{batch_metadata}')

# Basic preprocessing
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)

# Find highly variable genes
sc.pp.highly_variable_genes(adata, min_mean=0.0125, max_mean=3, min_disp=0.5)
adata.raw = adata
adata = adata[:, adata.var.highly_variable]

# Principal component analysis
sc.pp.scale(adata, max_value=10)
sc.tl.pca(adata, svd_solver='arpack')

# Simple batch integration (baseline)
sc.pp.neighbors(adata, n_neighbors=10, n_pcs=40)
sc.tl.umap(adata)

# Calculate silhouette score for batch integration quality
batch_labels = adata.obs['{batch_column}'].values
integrated_data = adata.obsm['X_umap']
""",
        
        "time_series_analysis": """
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_scaled_error
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA

# Load time series data
train_data = pd.read_csv('{train_data}')
test_data = pd.read_csv('{test_data}')

# Basic time series forecasting
train_data['ds'] = pd.to_datetime(train_data['ds'])
test_data['ds'] = pd.to_datetime(test_data['ds'])

# Simple baseline: AutoARIMA
sf = StatsForecast(
    models=[AutoARIMA(season_length=24)],
    freq='H'
)

# Fit and forecast
sf.fit(train_data)
forecasts = sf.predict(h={forecast_horizon})
""",
    }
    
    # Get template based on domain
    template = domain_templates.get(task_config.domain, domain_templates["machine_learning"])
    
    # Fill in template variables
    data_files = task_config.data_files
    code_reqs = task_config.code_requirements
    
    template_vars = {
        'train_file': data_files.get('train', 'train.csv'),
        'val_file': data_files.get('validation', 'val.csv'),
        'target_col': code_reqs.get('target_column', 'target'),
        'expression_matrix': data_files.get('expression_matrix', 'data.h5ad'),
        'batch_metadata': data_files.get('batch_metadata', 'batch_info.csv'),
        'batch_column': code_reqs.get('batch_column', 'batch'),
        'train_data': data_files.get('train_data', 'train.csv'),
        'forecast_horizon': code_reqs.get('forecast_horizon', 24),
    }
    
    try:
        return template.format(**template_vars)
    except KeyError as e:
        print(f"⚠️  Warning: Missing template variable {e}, using default template")
        return domain_templates["machine_learning"]

def main():
    """Main execution function."""
    args = parse_arguments()
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    # Load task configuration
    try:
        task_config = TaskConfiguration(args.task)
    except Exception as e:
        print(f"❌ Error loading task configuration: {e}")
        sys.exit(1)
    
    # Display task information
    display_task_info(task_config)
    
    # Create output directory
    output_dir = Path(args.output_dir) / f"{task_config.domain}_{task_config.task_name.replace(' ', '_')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Combine research ideas
    all_research_ideas = task_config.research_ideas.copy()
    if args.research_ideas:
        all_research_ideas.extend(args.research_ideas)
    
    # Create initial code prompt
    initial_prompt = create_initial_prompt(task_config)
    
    # Initialize the universal tree search
    try:
        from core.sandbox.universal_evaluator import UniversalCodeEvaluator
        from core.controller.search import SearchConfiguration
        
        # Create evaluator
        evaluator = UniversalCodeEvaluator(task_config)
        
        # Create search configuration
        search_config = SearchConfiguration(
            c_puct=args.c_puct,
            max_iterations=args.iterations
        )
        
        # Create search agent
        search_agent = UniversalTreeSearch(
            task_config=task_config,
            evaluator=evaluator.evaluate,
            search_config=search_config
        )
        
        print(f"🚀 Starting tree search with {args.iterations} iterations...")
        print(f"🎯 Target metric: {task_config.evaluation_metric}")
        print(f"💾 Results will be saved to: {output_dir}")
        print()
        
        # Run the search
        best_solution = search_agent.run(max_iterations=args.iterations)
        
        # Display results
        print("\n" + "=" * 70)
        print("🎉 Scientific Software Discovery Complete!")
        print("=" * 70)
        print(f"🏆 Best {task_config.evaluation_metric}: {best_solution.score:.6f}")
        print(f"🔬 Domain: {task_config.domain}")
        print(f"📊 Total Nodes Explored: {len(search_agent.nodes)}")
        print(f"💾 Results saved to: {output_dir}")
        
        # Save best solution
        best_code_file = output_dir / "best_solution.py"
        with open(best_code_file, 'w') as f:
            f.write(f"# Best solution for {task_config.task_name}\n")
            f.write(f"# {task_config.evaluation_metric}: {best_solution.score:.6f}\n\n")
            f.write(best_solution.code)
        
        print(f"💡 Best code saved to: {best_code_file}")
        
        if args.verbose:
            print(f"\n📝 Best Solution Code:")
            print("-" * 50)
            print(best_solution.code)
            
    except KeyboardInterrupt:
        print("\n⚠️  Search interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error during search: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()