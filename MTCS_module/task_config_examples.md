# Task Configuration Examples for Different Scientific Domains

This document provides ready-to-use task configuration templates for various scientific domains, demonstrating the universal nature of the AI system.

## 🧬 Bioinformatics: Single-cell RNA-seq Analysis

```yaml
# tasks/genomics_scrna/task_config.yaml
domain: "bioinformatics"
task_name: "Single-cell RNA-seq Batch Integration"
description: |
  Remove batch effects from single-cell RNA sequencing data while preserving
  biological signal. The goal is to integrate multiple batches of scRNA-seq data
  to enable downstream analysis across datasets. Success is measured by how well
  the integration preserves biological variation while removing technical variation.

evaluation_metric: "silhouette_score"
higher_is_better: true
secondary_metrics: ["ARI", "NMI", "kBET"]

data_files:
  expression_matrix: "expression_data.h5ad"
  batch_metadata: "batch_info.csv"
  cell_types: "cell_type_annotations.csv"

code_requirements:
  input_format: "AnnData"
  output_format: "AnnData"
  required_libraries: ["scanpy", "pandas", "numpy", "anndata", "sklearn"]
  batch_column: "batch"
  cell_type_column: "cell_type"
  output_variable: "integrated_data"

research_ideas:
  - "Combine ComBat batch correction with BBKNN neighborhood integration"
  - "Use Harmony for batch integration with principal component analysis"
  - "Apply Seurat CCA integration followed by UMAP embedding"
  - "Implement mutual nearest neighbors (MNN) correction"
```

## 🌍 Geospatial Analysis: Satellite Image Segmentation

```yaml
# tasks/satellite_segmentation/task_config.yaml
domain: "geospatial_analysis"
task_name: "Semantic Segmentation of Remote Sensing Images"
description: |
  Perform dense pixel-wise multi-label semantic segmentation of satellite images.
  Classify each pixel into categories such as building, forest, water, road, etc.
  The model should handle high-resolution remote sensing data and achieve 
  state-of-the-art performance on standard benchmarks.

evaluation_metric: "mIoU"
higher_is_better: true
secondary_metrics: ["pixel_accuracy", "mean_pixel_accuracy", "frequency_weighted_IoU"]

data_files:
  train_images: "images/train/"
  train_masks: "masks/train/"
  val_images: "images/val/"
  val_masks: "masks/val/"
  class_names: "class_mapping.json"

code_requirements:
  input_format: "RGB images (H x W x 3)"
  output_format: "segmentation masks (H x W)"
  required_libraries: ["torch", "torchvision", "cv2", "numpy", "albumentations"]
  num_classes: 7
  image_size: [512, 512]
  output_variable: "segmentation_predictions"

research_ideas:
  - "Use UNet++ architecture with EfficientNet encoder"
  - "Apply DeepLabV3+ with Xception backbone"
  - "Implement SegFormer with hierarchical transformer"
  - "Use advanced data augmentation: MixUp, CutMix, Albumentations"
  - "Apply test-time augmentation (TTA) for better performance"
```

## 📈 Time Series: Multi-domain Forecasting

```yaml
# tasks/time_series_forecasting/task_config.yaml
domain: "time_series_analysis"
task_name: "Multi-domain Time Series Forecasting"
description: |
  Develop a general-purpose time series forecasting model that can adapt to
  diverse datasets across different domains (finance, weather, energy, etc.).
  The model should automatically adapt to different seasonal patterns, trends,
  and data characteristics without domain-specific tuning.

evaluation_metric: "MASE"
higher_is_better: false
secondary_metrics: ["RMSE", "MAPE", "sMAPE", "WAPE"]

data_files:
  train_data: "train_series.csv"
  test_data: "test_series.csv"
  metadata: "series_metadata.json"

code_requirements:
  input_format: "time series with datetime index"
  output_format: "forecasted values"
  required_libraries: ["pandas", "numpy", "statsforecast", "neuralforecast", "sklearn"]
  forecast_horizon: 24
  output_variable: "forecasts"

research_ideas:
  - "Use N-BEATS neural network with interpretable components"
  - "Apply Transformer models with positional encoding for seasonality"
  - "Implement ensemble of statistical and ML models (ARIMA + XGBoost)"
  - "Use AutoML approach with automatic feature engineering"
  - "Apply meta-learning to quickly adapt to new time series"
```

## 🧠 Neuroscience: Brain Activity Prediction

```yaml
# tasks/neural_activity/task_config.yaml
domain: "neuroscience"
task_name: "Whole-brain Neural Activity Prediction"
description: |
  Predict neural activity patterns in zebrafish brain from stimulus data.
  The task involves multivariate time-series forecasting of calcium imaging
  data across thousands of neurons. Models should capture both spatial and
  temporal dependencies in neural dynamics.

evaluation_metric: "MAE"
higher_is_better: false
secondary_metrics: ["RMSE", "correlation", "explained_variance"]

data_files:
  neural_data: "calcium_traces.npy"
  stimulus_data: "stimulus_patterns.npy"
  brain_anatomy: "neuron_coordinates.csv"
  
code_requirements:
  input_format: "multivariate time series (time x neurons)"
  output_format: "predicted neural activity"
  required_libraries: ["numpy", "torch", "sklearn", "scipy"]
  sequence_length: 100
  prediction_horizon: 10
  output_variable: "predicted_activity"

research_ideas:
  - "Use 3D CNN to capture spatial brain organization"
  - "Apply LSTM with attention mechanism for temporal dependencies"
  - "Implement Graph Neural Networks using brain connectivity"
  - "Use Transformer architecture with spatial-temporal embeddings"
  - "Apply physics-informed neural networks with biophysical constraints"
```

## 🦠 Epidemiology: Disease Forecasting

```yaml
# tasks/covid_forecasting/task_config.yaml
domain: "epidemiology" 
task_name: "COVID-19 Hospitalization Forecasting"
description: |
  Forecast COVID-19 hospitalizations for CDC ensemble predictions.
  Models should incorporate multiple data sources including case counts,
  mobility data, vaccination rates, and historical patterns. Predictions
  should be robust across different geographic regions and time periods.

evaluation_metric: "WIS"
higher_is_better: false
secondary_metrics: ["MAPE", "coverage_probability", "quantile_score"]

data_files:
  case_data: "daily_cases.csv"
  hospitalization_data: "daily_hospitalizations.csv"
  mobility_data: "mobility_trends.csv"
  vaccination_data: "vaccination_rates.csv"
  demographics: "population_demographics.csv"

code_requirements:
  input_format: "panel data (location x time)"
  output_format: "quantile predictions"
  required_libraries: ["pandas", "numpy", "statsmodels", "sklearn", "pytorch"]
  forecast_horizon: 28
  quantiles: [0.1, 0.25, 0.5, 0.75, 0.9]
  output_variable: "hospitalization_forecasts"

research_ideas:
  - "Use hierarchical Bayesian models for geographic pooling"
  - "Apply ensemble of epidemiological models (SIR, SEIR) and ML"
  - "Implement attention-based sequence models for mobility integration"
  - "Use quantile regression forests for uncertainty quantification"
  - "Apply transfer learning across geographic regions"
```

## 🧪 Drug Discovery: Molecular Property Prediction

```yaml
# tasks/drug_discovery/task_config.yaml
domain: "drug_discovery"
task_name: "Molecular Property Prediction"
description: |
  Predict drug-like properties of molecules from their chemical structure.
  Focus on ADMET properties (Absorption, Distribution, Metabolism, Excretion, Toxicity)
  that are critical for drug development. Models should work with SMILES strings
  or molecular graphs and achieve pharmaceutical industry standards.

evaluation_metric: "RMSE"
higher_is_better: false
secondary_metrics: ["MAE", "R2", "spearman_correlation"]

data_files:
  molecules: "molecules.smi"
  properties: "molecular_properties.csv"
  train_split: "train_indices.txt"
  test_split: "test_indices.txt"

code_requirements:
  input_format: "SMILES strings"
  output_format: "predicted properties"
  required_libraries: ["rdkit", "torch", "sklearn", "numpy", "pandas"]
  property_columns: ["logP", "solubility", "permeability", "toxicity"]
  output_variable: "property_predictions"

research_ideas:
  - "Use Graph Neural Networks (GCN, GAT) on molecular graphs"
  - "Apply pre-trained molecular transformers (ChemBERTa, MolT5)"
  - "Implement message passing neural networks (MPNN)"
  - "Use molecular fingerprints with ensemble methods"
  - "Apply multi-task learning across related properties"
```

## 🌡️ Climate Science: Weather Prediction

```yaml
# tasks/climate_forecasting/task_config.yaml
domain: "climate_science"
task_name: "Regional Weather Pattern Prediction"
description: |
  Predict regional weather patterns including temperature, precipitation,
  and extreme events. Models should incorporate multiple atmospheric variables,
  seasonal patterns, and climate change trends. Focus on medium-range forecasts
  (7-30 days) that bridge weather and climate timescales.

evaluation_metric: "RMSE"
higher_is_better: false
secondary_metrics: ["MAE", "pattern_correlation", "extreme_event_detection"]

data_files:
  reanalysis_data: "era5_data.nc"
  station_observations: "weather_stations.csv"
  geographic_features: "topography.nc"
  climate_indices: "teleconnection_indices.csv"

code_requirements:
  input_format: "gridded atmospheric data (lat x lon x time x variables)"
  output_format: "weather forecasts"
  required_libraries: ["xarray", "numpy", "torch", "sklearn", "cartopy"]
  forecast_horizon: 30
  variables: ["temperature", "precipitation", "pressure", "humidity"]
  output_variable: "weather_forecasts"

research_ideas:
  - "Use ConvLSTM for spatiotemporal weather dynamics"
  - "Apply Vision Transformers adapted for meteorological data"
  - "Implement physics-informed neural networks with atmospheric equations"
  - "Use ensemble methods combining numerical weather models and ML"
  - "Apply attention mechanisms for teleconnection patterns"
```

## 🔢 Numerical Analysis: Scientific Computing

```yaml
# tasks/numerical_integration/task_config.yaml
domain: "numerical_analysis"
task_name: "Difficult Integral Computation"
description: |
  Develop robust numerical methods for computing difficult integrals where
  standard libraries fail. Focus on integrals with singularities, oscillatory
  behavior, or infinite domains. The method should outperform scipy.integrate.quad
  on challenging test cases from mathematical physics and engineering.

evaluation_metric: "log_absolute_fractional_error"
higher_is_better: false
secondary_metrics: ["success_rate", "computation_time", "stability"]

data_files:
  test_integrals: "integral_test_suite.json"
  analytical_solutions: "exact_solutions.json"
  difficulty_ratings: "integral_difficulty.csv"

code_requirements:
  input_format: "mathematical functions (symbolic or callable)"
  output_format: "numerical integral values"
  required_libraries: ["numpy", "scipy", "sympy", "math"]
  error_tolerance: 1e-10
  output_variable: "integral_estimates"

research_ideas:
  - "Apply adaptive quadrature with error estimation"
  - "Use domain partitioning for infinite integrals"
  - "Implement Euler transformation for convergence acceleration"
  - "Apply Monte Carlo methods for high-dimensional integrals"
  - "Use machine learning to select optimal integration strategies"
```

## 🏭 Materials Science: Crystal Structure Prediction

```yaml
# tasks/materials_discovery/task_config.yaml
domain: "materials_science"
task_name: "Crystal Structure Prediction and Property Optimization"
description: |
  Predict crystal structures and optimize material properties for specific
  applications. Given chemical composition, predict stable crystal structures
  and their properties (bandgap, conductivity, mechanical properties).
  Focus on discovering novel materials for energy applications.

evaluation_metric: "formation_energy_error"
higher_is_better: false
secondary_metrics: ["structure_similarity", "property_prediction_accuracy"]

data_files:
  crystal_structures: "structures.cif"
  material_properties: "properties.json"
  composition_data: "compositions.csv"
  
code_requirements:
  input_format: "crystal structures (CIF format)"
  output_format: "predicted structures and properties"
  required_libraries: ["pymatgen", "ase", "torch", "sklearn", "numpy"]
  property_targets: ["formation_energy", "bandgap", "bulk_modulus"]
  output_variable: "predicted_structures"

research_ideas:
  - "Use Crystal Graph Convolutional Networks (CGCNN)"
  - "Apply structure generation with VAE or GAN"
  - "Implement multi-objective optimization for property targets"
  - "Use transfer learning from existing materials databases"
  - "Apply active learning for efficient materials discovery"
```

These task configurations demonstrate how the AI system can be applied to virtually any scientific domain by simply defining the problem structure, data format, and evaluation metrics. The system's universal architecture allows it to automatically adapt its code generation and optimization strategies to each domain's specific requirements.