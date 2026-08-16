"""
Task Configuration Manager for Universal Scientific AI System
===========================================================

Handles loading and managing task-specific configurations from YAML files.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field


@dataclass
class TaskConfiguration:
    """Configuration for a scientific task."""
    
    # Core task properties
    task_name: str
    domain: str
    description: str
    evaluation_metric: str
    higher_is_better: bool = True
    
    # Data files
    data_files: Dict[str, str] = field(default_factory=dict)
    
    # Code requirements
    code_requirements: Dict[str, Any] = field(default_factory=dict)
    
    # Research context
    research_ideas: List[str] = field(default_factory=list)
    baseline_performance: Dict[str, float] = field(default_factory=dict)
    
    # Competition/additional info
    competition_info: Dict[str, Any] = field(default_factory=dict)
    
    def __init__(self, config_path: str):
        """
        Initialize task configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        
        # Load and parse YAML
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Set core properties
        self.task_name = config_data.get('task_name', 'Unknown Task')
        self.domain = config_data.get('domain', 'machine_learning')
        self.description = config_data.get('description', '')
        self.evaluation_metric = config_data.get('evaluation_metric', 'accuracy')
        self.higher_is_better = config_data.get('higher_is_better', True)
        
        # Process data files (require absolute paths only)
        self.data_files = {}
        data_files_config = config_data.get('data_files', {})
        for key, path in data_files_config.items():
            if not os.path.isabs(path):
                raise ValueError(f"Data file path must be absolute: {key}={path}. Please use absolute paths in your YAML configuration.")
            self.data_files[key] = path
        
        # Set other properties
        self.secondary_metrics = config_data.get('secondary_metrics', [])
        self.code_requirements = config_data.get('code_requirements', {})
        self.research_ideas = config_data.get('research_ideas', [])
        self.baseline_performance = config_data.get('baseline_performance', {})
        self.competition_info = config_data.get('competition_info', {})
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate that the configuration is complete and correct."""
        errors = []
        
        # Check required fields
        if not self.task_name:
            errors.append("Task name is required")
        
        if not self.description:
            errors.append("Task description is required")
        
        # Validate data files exist
        for key, path in self.data_files.items():
            if not os.path.exists(path):
                errors.append(f"Data file not found: {path}")
        
        # Validate evaluation metric
        valid_metrics = ['accuracy', 'auc', 'f1', 'precision', 'recall', 'rmse', 'mae', 'r2', 'mse', 'mape', 'miou']
        if self.evaluation_metric.lower() not in valid_metrics:
            # Allow custom metrics, just warn
            print(f"⚠️ Warning: Custom evaluation metric '{self.evaluation_metric}' - ensure evaluator supports it")
        
        if errors:
            raise ValueError(f"Invalid task configuration: {'; '.join(errors)}")
    
    def get_target_column(self) -> str:
        """Get the target column name for prediction."""
        return self.code_requirements.get('target_column', 'target')
    
    def get_prediction_format(self) -> str:
        """Get the required prediction format."""
        return self.code_requirements.get('prediction_format', 'array')
    
    def get_output_variable(self) -> str:
        """Get the required output variable name."""
        return self.code_requirements.get('output_variable', 'predictions')
    
    def get_data_preparation_info(self) -> Dict[str, Any]:
        """Get information needed for data preparation."""
        return {
            'data_files': self.data_files,
            'target_column': self.get_target_column(),
            'evaluation_metric': self.evaluation_metric,
            'higher_is_better': self.higher_is_better
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'task_name': self.task_name,
            'domain': self.domain,
            'description': self.description,
            'evaluation_metric': self.evaluation_metric,
            'higher_is_better': self.higher_is_better,
            'data_files': self.data_files,
            'code_requirements': self.code_requirements,
            'research_ideas': self.research_ideas,
            'baseline_performance': self.baseline_performance,
            'competition_info': self.competition_info
        }
    
    def create_prompt_context(self, include_research_ideas: bool = False) -> str:
        """
        Create a formatted context string for prompts.
        
        Args:
            include_research_ideas: Whether to include research ideas in context
            
        Returns:
            Formatted context string
        """
        context_parts = [
            f"Task: {self.task_name}",
            f"Domain: {self.domain}",
            f"Description: {self.description}",
            f"Evaluation Metric: {self.evaluation_metric}",
            f"Higher is Better: {self.higher_is_better}"
        ]
        
        # Add secondary metrics if available
        if hasattr(self, 'secondary_metrics') and self.secondary_metrics:
            context_parts.append(f"Secondary Metrics: {', '.join(self.secondary_metrics)}")
        
        # Add data files with full paths
        if self.data_files:
            context_parts.append("Data Files:")
            for key, path in self.data_files.items():
                context_parts.append(f"- {key}: {path}")
        
        # Add code requirements
        if hasattr(self, 'code_requirements') and self.code_requirements:
            context_parts.append("Code Requirements:")
            
            # Highlight embedding model first if specified (critical requirement)
            if 'embedding_model' in self.code_requirements:
                context_parts.append(f"- **REQUIRED EMBEDDING MODEL**: {self.code_requirements['embedding_model']}")
                if 'embedding_model_info' in self.code_requirements:
                    context_parts.append(f"- Embedding Model Details: {self.code_requirements['embedding_model_info']}")
            
            for key, value in self.code_requirements.items():
                # Skip already-processed embedding model keys
                if key in ['embedding_model', 'embedding_model_info']:
                    continue
                elif key == 'required_libraries':
                    context_parts.append(f"- Required Libraries: {', '.join(value)}")
                elif key == 'feature_columns':
                    context_parts.append(f"- Feature Columns: {', '.join(value)}")
                elif key == 'exclude_columns':
                    context_parts.append(f"- Exclude Columns: {', '.join(value)}")
                else:
                    context_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        # Add baseline performance if available
        if hasattr(self, 'baseline_performance') and self.baseline_performance:
            context_parts.append("Baseline Performance:")
            for method, score in self.baseline_performance.items():
                context_parts.append(f"- {method.replace('_', ' ').title()}: {score}")
        
        # Add competition info if available
        if hasattr(self, 'competition_info') and self.competition_info:
            context_parts.append("Dataset Information:")
            for key, value in self.competition_info.items():
                context_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        if include_research_ideas and self.research_ideas:
            context_parts.append("Research Ideas:")
            for idea in self.research_ideas[:3]:  # Show first 3
                context_parts.append(f"- {idea}")
            if len(self.research_ideas) > 3:
                context_parts.append(f"- ... and {len(self.research_ideas) - 3} more")
        
        return "\n".join(context_parts)
    
    def load_data(self, data_key: Optional[str] = None) -> Union[Dict[str, str], Any]:
        """
        Load data files for the task.
        
        Args:
            data_key: Optional key to load specific data file ('train', 'validation', etc.)
                     If None, returns all data files as a dictionary
                     
        Returns:
            pandas.DataFrame if data_key specified, dict if data_key is None
        """
        if data_key is None:
            # Return all data files as a dictionary
            return self.data_files
        
        if data_key not in self.data_files:
            raise ValueError(f"Data key '{data_key}' not found. Available keys: {list(self.data_files.keys())}")
        
        data_path = self.data_files[data_key]
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found: {data_path}")
        
        try:
            import pandas as pd
            df = pd.read_csv(data_path)
            return df
        except Exception as e:
            raise RuntimeError(f"Failed to load data from {data_path}: {str(e)}")
    
    def get_data_file_path(self, data_key: str) -> str:
        """
        Get the file path for a specific data key.
        
        Args:
            data_key: The data key ('train', 'validation', etc.)
            
        Returns:
            File path string
        """
        if data_key not in self.data_files:
            raise ValueError(f"Data key '{data_key}' not found. Available keys: {list(self.data_files.keys())}")
        
        return self.data_files[data_key]
    
    def __repr__(self) -> str:
        return f"TaskConfiguration(task_name='{self.task_name}', domain='{self.domain}', metric='{self.evaluation_metric}')"


def load_task_configuration(config_path: str) -> TaskConfiguration:
    """
    Load task configuration from YAML file.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        TaskConfiguration instance
    """
    return TaskConfiguration(config_path)


def create_sample_task_config(output_path: str, 
                            task_name: str,
                            domain: str = "machine_learning",
                            description: str = "Sample scientific task"):
    """
    Create a sample task configuration file.
    
    Args:
        output_path: Where to save the configuration
        task_name: Name of the task
        domain: Domain of the task
        description: Description of the task
    """
    sample_config = {
        'task_name': task_name,
        'domain': domain,
        'description': description,
        'evaluation_metric': 'auc',
        'higher_is_better': True,
        'data_files': {
            'train': 'data/train.csv',
            'test': 'data/test.csv',
            'validation': 'data/validation.csv'
        },
        'code_requirements': {
            'target_column': 'target',
            'prediction_format': 'array',
            'output_variable': 'predictions'
        },
        'research_ideas': [
            'Try ensemble methods',
            'Explore feature engineering',
            'Consider deep learning approaches'
        ],
        'baseline_performance': {
            'logistic_regression': 0.75,
            'random_forest': 0.82
        },
        'competition_info': {
            'source': 'sample',
            'metric_description': 'Area under the ROC curve'
        }
    }
    
    with open(output_path, 'w') as f:
        yaml.dump(sample_config, f, default_flow_style=False, indent=2)
    
    print(f"Sample configuration saved to: {output_path}")


# Example usage and testing
if __name__ == "__main__":
    # Create a sample configuration for testing
    sample_path = "sample_task_config.yaml"
    create_sample_task_config(
        sample_path,
        "Sample Binary Classification",
        "machine_learning",
        "A sample binary classification task for testing"
    )
    
    # Load and test the configuration
    try:
        config = load_task_configuration(sample_path)
        print(f"✅ Configuration loaded successfully: {config}")
        print(f"📊 Data files: {config.data_files}")
        print(f"🎯 Target column: {config.get_target_column()}")
        print(f"📈 Metric: {config.evaluation_metric}")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
    finally:
        # Clean up sample file
        if os.path.exists(sample_path):
            os.remove(sample_path)