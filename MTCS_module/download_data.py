#!/usr/bin/env python3
"""
Data Downloader for Binary Classification of Machine Failures
==============================================================

This script automatically downloads the AI4I 2020 Predictive Maintenance Dataset
used for binary classification of machine failures.

The dataset contains:
- Air temperature [K]
- Process temperature [K] 
- Rotational speed [rpm]
- Torque [Nm]
- Tool wear [min]
- Machine failure (target variable)
- Failure type (Heat Dissipation, Power, Overstrain, Tool Wear, Random)

Usage:
    python download_data.py

The script will:
1. Create a 'data' directory if it doesn't exist
2. Download the dataset from multiple sources
3. Verify the downloaded data
4. Create train/test splits compatible with the AviaAutoML system
"""

import os
import sys
import requests
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from pathlib import Path
import zipfile
import io
import warnings

warnings.filterwarnings('ignore')

# Dataset URLs (multiple sources for reliability)
DATASET_SOURCES = [
    {
        'name': 'UCI ML Repository',
        'url': 'https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip',
        'description': 'Official UCI Machine Learning Repository'
    },
    {
        'name': 'Backup Source',
        'url': 'https://raw.githubusercontent.com/selva86/datasets/master/ai4i2020.csv',
        'description': 'Direct CSV download from GitHub'
    }
]

def create_data_directory():
    """Create data directory if it doesn't exist."""
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    print(f"✅ Data directory created: {data_dir.absolute()}")
    return data_dir

def download_from_uci():
    """Download dataset from UCI ML Repository."""
    try:
        print("🔄 Attempting to download from UCI ML Repository...")
        url = DATASET_SOURCES[0]['url']
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Extract ZIP file
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            # Find the CSV file in the ZIP
            csv_files = [f for f in zip_file.namelist() if f.endswith('.csv')]
            if not csv_files:
                raise Exception("No CSV file found in ZIP archive")
            
            # Extract the first CSV file
            csv_data = zip_file.read(csv_files[0])
            df = pd.read_csv(io.BytesIO(csv_data))
            
        print(f"✅ Successfully downloaded from UCI (shape: {df.shape})")
        return df
        
    except Exception as e:
        print(f"❌ Failed to download from UCI: {str(e)}")
        return None

def download_from_github():
    """Download dataset directly from GitHub backup."""
    try:
        print("🔄 Attempting to download from GitHub backup...")
        url = DATASET_SOURCES[1]['url']
        
        df = pd.read_csv(url)
        print(f"✅ Successfully downloaded from GitHub (shape: {df.shape})")
        return df
        
    except Exception as e:
        print(f"❌ Failed to download from GitHub: {str(e)}")
        return None

def create_synthetic_data():
    """Create synthetic dataset with similar characteristics if download fails."""
    print("🔄 Creating synthetic dataset as fallback...")
    
    np.random.seed(42)
    n_samples = 10000
    
    # Generate synthetic features based on the original dataset characteristics
    data = {
        'UDI': range(1, n_samples + 1),
        'Product ID': [f'M{np.random.randint(100000, 999999)}' for _ in range(n_samples)],
        'Type': np.random.choice(['L', 'M', 'H'], n_samples, p=[0.6, 0.3, 0.1]),
        'Air temperature [K]': np.random.normal(300, 2, n_samples),
        'Process temperature [K]': np.random.normal(310, 1.5, n_samples),
        'Rotational speed [rpm]': np.random.normal(1500, 100, n_samples),
        'Torque [Nm]': np.random.normal(40, 10, n_samples),
        'Tool wear [min]': np.random.randint(0, 250, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Generate realistic failure patterns
    # Higher temperatures, extreme torque, and tool wear increase failure probability
    failure_prob = (
        0.01 +  # Base failure rate
        0.02 * (df['Air temperature [K]'] > 302) +  # High air temp
        0.03 * (df['Process temperature [K]'] > 312) +  # High process temp
        0.04 * (df['Torque [Nm]'] > 50) +  # High torque
        0.05 * (df['Tool wear [min]'] > 200)  # High tool wear
    )
    
    # Generate failures based on probability
    df['Machine failure'] = np.random.binomial(1, failure_prob)
    
    # Generate failure types for failed machines
    failure_types = []
    for _, row in df.iterrows():
        if row['Machine failure'] == 1:
            if row['Process temperature [K]'] > 312:
                failure_types.append('Heat Dissipation Failure')
            elif row['Torque [Nm]'] > 50:
                failure_types.append('Power Failure')
            elif row['Tool wear [min]'] > 200:
                failure_types.append('Tool Wear Failure')
            elif row['Air temperature [K]'] > 302:
                failure_types.append('Overstrain Failure')
            else:
                failure_types.append('Random Failures')
        else:
            failure_types.append('No Failure')
    
    df['Failure Type'] = failure_types
    
    print(f"✅ Created synthetic dataset (shape: {df.shape})")
    print(f"   Failure rate: {df['Machine failure'].mean():.1%}")
    return df


def verify_dataset(df):
    """Verify the dataset has the expected structure and process failure types."""
    required_columns = [
        'UDI', 'Product ID', 'Type', 'Air temperature [K]',
        'Process temperature [K]', 'Rotational speed [rpm]',
        'Torque [Nm]', 'Tool wear [min]', 'Machine failure'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"❌ Missing required columns: {missing_columns}")
        return False
    
    # Check if we have failure type columns to process
    failure_columns = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']
    has_failure_columns = all(col in df.columns for col in failure_columns)
    
    if has_failure_columns:
        print("🔄 Processing failure type columns...")
        # Process failure types in place
        failure_mapping = {
            'TWF': 'Tool Wear Failure',
            'HDF': 'Heat Dissipation Failure',
            'PWF': 'Power Failure', 
            'OSF': 'Overstrain Failure',
            'RNF': 'Random Failures'
        }
        
        failure_types = []
        for _, row in df.iterrows():
            if row['Machine failure'] == 0:
                failure_types.append('No Failure')
            else:
                # Check which failure type(s) are active
                active_failures = [col for col in failure_columns if row[col] == 1]
                if active_failures:
                    # Use the first active failure type
                    failure_types.append(failure_mapping[active_failures[0]])
                else:
                    failure_types.append('No Failure')
        
        df['Failure Type'] = failure_types
        
    elif 'Failure Type' not in df.columns:
        print("⚠️  No failure type information found. Adding default failure types...")
        df['Failure Type'] = df['Machine failure'].apply(
            lambda x: 'No Failure' if x == 0 else 'Unknown Failure'
        )
    
    print("✅ Dataset structure verified")
    print(f"   Samples: {len(df):,}")
    print(f"   Features: {len(df.columns)}")
    print(f"   Failure rate: {df['Machine failure'].mean():.1%}")
    
    if 'Failure Type' in df.columns:
        failure_dist = df['Failure Type'].value_counts().to_dict()
        print(f"   Failure types: {failure_dist}")
    
    return True

def create_train_test_splits(df, data_dir):
    """Create train/test splits compatible with AviaAutoML system."""
    print("🔄 Creating train/test splits...")
    
    # Create stratified split to ensure balanced failure rates
    train_df, test_df = train_test_split(
        df, 
        test_size=0.2, 
        random_state=42, 
        stratify=df['Machine failure']
    )
    
    # Save full dataset
    df.to_csv(data_dir / 'full_dataset.csv', index=False)
    
    # Save train/test splits
    train_df.to_csv(data_dir / 'train.csv', index=False)
    test_df.to_csv(data_dir / 'test.csv', index=False)
    
    # Create sample submission file (for Kaggle-style format)
    sample_submission = pd.DataFrame({
        'id': test_df['UDI'],
        'Machine failure': 0  # Placeholder predictions
    })
    sample_submission.to_csv(data_dir / 'sample_submission.csv', index=False)
    
    print(f"✅ Created data splits:")
    print(f"   Train set: {len(train_df):,} samples")
    print(f"   Test set: {len(test_df):,} samples")
    print(f"   Files saved in: {data_dir.absolute()}")
    
    return train_df, test_df

def main():
    """Main function to download and prepare the dataset."""
    print("🚀 Binary Classification of Machine Failures - Data Downloader")
    print("=" * 65)
    
    # Create data directory
    data_dir = create_data_directory()
    
    # Check if data already exists
    if (data_dir / 'train.csv').exists() and (data_dir / 'test.csv').exists():
        print("✅ Dataset already exists! Skipping download.")
        print(f"   Files found in: {data_dir.absolute()}")
        
        # Show existing data info
        train_df = pd.read_csv(data_dir / 'train.csv')
        test_df = pd.read_csv(data_dir / 'test.csv')
        print(f"   Train set: {len(train_df):,} samples")
        print(f"   Test set: {len(test_df):,} samples")
        return
    
    # Try to download from multiple sources
    df = None
    
    # Try UCI first
    df = download_from_uci()
    
    # Try GitHub backup if UCI fails
    if df is None:
        df = download_from_github()
    
    # Create synthetic data if all downloads fail
    if df is None:
        print("⚠️  All download sources failed. Creating synthetic dataset...")
        df = create_synthetic_data()
    
    # Verify and process dataset
    if not verify_dataset(df):
        print("❌ Dataset verification failed!")
        sys.exit(1)
    
    # Create train/test splits
    create_train_test_splits(df, data_dir)
    
    print("\n🎉 Dataset download and preparation completed!")
    print("\nNext steps:")
    print("1. Review the data in the 'data' directory")
    print("2. Run the AviaAutoML system: python main.py")
    print("3. The system will use train.csv for training and test.csv for evaluation")

if __name__ == "__main__":
    main()