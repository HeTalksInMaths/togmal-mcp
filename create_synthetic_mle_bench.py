#!/usr/bin/env python3
"""
Create Synthetic MLE-Bench Style Dataset
=========================================

Since we can't download real MLE-Bench data, create realistic synthetic
Kaggle competition questions based on common ML engineering tasks.

This demonstrates the integration pattern for when real data becomes available.
"""

import json
from pathlib import Path
from datetime import datetime

def create_synthetic_mle_bench():
    """Create synthetic Kaggle-style ML competition questions"""

    competitions = [
        {
            "question_id": "mle_synth_titanic",
            "question_text": """Kaggle Competition: Titanic - Machine Learning from Disaster

**Goal**: Predict survival on the Titanic based on passenger information.

**Dataset**: 891 training samples, 418 test samples
**Features**: PassengerId, Pclass, Name, Sex, Age, SibSp, Parch, Ticket, Fare, Cabin, Embarked
**Target**: Survived (0 = No, 1 = Yes)

**Evaluation Metric**: Accuracy (percentage of passengers correctly predicted)

**Task**: Build a model to predict which passengers survived the Titanic shipwreck.

**Difficulty**: Getting Started (Beginner)
**Competition Type**: Binary Classification
            """,
            "domain": "Machine Learning",
            "subdomain": "Binary Classification",
            "difficulty_score": 0.2,  # Getting Started = easy
            "source_benchmark": "MLE-Bench (Synthetic)",
            "competition_tier": "Getting Started",
            "evaluation_metrics": ["accuracy"],
            "solution": {
                "winning_approach": "Ensemble of Random Forest + Gradient Boosting",
                "key_techniques": [
                    "feature_engineering",
                    "handling_missing_values",
                    "categorical_encoding",
                    "ensembling"
                ],
                "features_engineered": [
                    "Family_Size = SibSp + Parch + 1",
                    "Title extraction from Name",
                    "Age binning",
                    "Fare binning"
                ],
                "model_details": {
                    "model_type": "Ensemble (RF + XGBoost)",
                    "hyperparameters": {
                        "rf_n_estimators": 100,
                        "xgb_learning_rate": 0.1,
                        "xgb_max_depth": 5
                    }
                },
                "code_snippet": """
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import cross_val_score

# Feature engineering
def engineer_features(df):
    df['Family_Size'] = df['SibSp'] + df['Parch'] + 1
    df['Title'] = df['Name'].str.extract(' ([A-Za-z]+)\.', expand=False)
    df['Age_Bin'] = pd.cut(df['Age'], bins=[0, 12, 18, 35, 60, 100], labels=[1,2,3,4,5])
    return df

# Train ensemble
rf = RandomForestClassifier(n_estimators=100, random_state=42)
gb = GradientBoostingClassifier(learning_rate=0.1, max_depth=5, random_state=42)

# Ensemble predictions
predictions = (rf.predict_proba(X_test)[:, 1] + gb.predict_proba(X_test)[:, 1]) / 2
final_preds = (predictions > 0.5).astype(int)
                """,
                "performance": {
                    "leaderboard_score": 0.82,  # Top 10% accuracy
                    "cv_score": 0.84,
                    "rank_percentile": 90
                },
                "lessons_learned": [
                    "Feature engineering is crucial - Family_Size was highly predictive",
                    "Title extraction captured social status (Mrs., Mr., Master, etc.)",
                    "Ensemble methods outperform single models",
                    "Careful handling of missing Age values improved performance"
                ]
            },
            "dataset_info": {
                "n_samples": 891,
                "n_features": 12,
                "n_test": 418,
                "missing_data": "Age (20%), Cabin (77%), Embarked (0.2%)"
            }
        },
        {
            "question_id": "mle_synth_house_prices",
            "question_text": """Kaggle Competition: House Prices - Advanced Regression Techniques

**Goal**: Predict house sale prices based on 79 explanatory variables.

**Dataset**: 1,460 training samples, 1,459 test samples
**Features**: 79 features including lot size, neighborhood, quality ratings, number of rooms, etc.
**Target**: SalePrice (continuous)

**Evaluation Metric**: RMSE (Root Mean Squared Error) on log-transformed prices

**Task**: Build a regression model to predict house prices in Ames, Iowa.

**Difficulty**: Playground (Intermediate)
**Competition Type**: Regression
            """,
            "domain": "Machine Learning",
            "subdomain": "Regression",
            "difficulty_score": 0.45,
            "source_benchmark": "MLE-Bench (Synthetic)",
            "competition_tier": "Playground",
            "evaluation_metrics": ["rmse", "rmsle"],
            "solution": {
                "winning_approach": "Stacked ensemble with feature engineering",
                "key_techniques": [
                    "advanced_feature_engineering",
                    "handling_outliers",
                    "log_transformation",
                    "stacking",
                    "regularization"
                ],
                "features_engineered": [
                    "TotalSF = TotalBsmtSF + 1stFlrSF + 2ndFlrSF",
                    "Total_Bathrooms = FullBath + 0.5*HalfBath + BsmtFullBath + 0.5*BsmtHalfBath",
                    "Age = YrSold - YearBuilt",
                    "Polynomial features for quality ratings"
                ],
                "model_details": {
                    "model_type": "Stacked ensemble",
                    "base_models": ["Ridge", "Lasso", "ElasticNet", "GradientBoosting", "XGBoost", "LightGBM"],
                    "meta_model": "Ridge regression",
                    "hyperparameters": {
                        "ridge_alpha": 10.0,
                        "lasso_alpha": 0.0005,
                        "xgb_learning_rate": 0.05,
                        "lgb_num_leaves": 31
                    }
                },
                "code_snippet": """
import numpy as np
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import GradientBoostingRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from mlxtend.regressor import StackingCVRegressor

# Feature engineering
def engineer_features(df):
    df['TotalSF'] = df['TotalBsmtSF'] + df['1stFlrSF'] + df['2ndFlrSF']
    df['Total_Bathrooms'] = df['FullBath'] + 0.5*df['HalfBath'] + df['BsmtFullBath'] + 0.5*df['BsmtHalfBath']
    df['Age'] = df['YrSold'] - df['YearBuilt']
    return df

# Stacking ensemble
ridge = Ridge(alpha=10.0)
lasso = Lasso(alpha=0.0005)
xgb = XGBRegressor(learning_rate=0.05, n_estimators=1000)
lgb = LGBMRegressor(num_leaves=31)

stack = StackingCVRegressor(
    regressors=[ridge, lasso, xgb, lgb],
    meta_regressor=Ridge(alpha=10.0),
    cv=5,
    use_features_in_secondary=True
)

# Train on log-transformed target
y_train_log = np.log1p(y_train)
stack.fit(X_train, y_train_log)

# Predict and inverse transform
predictions = np.expm1(stack.predict(X_test))
                """,
                "performance": {
                    "leaderboard_score": 0.11542,  # RMSLE - Top 5%
                    "cv_score": 0.11234,
                    "rank_percentile": 95
                },
                "lessons_learned": [
                    "Log transformation critical for RMSLE metric",
                    "Stacking significantly improved over single models",
                    "Feature engineering (TotalSF, Age) added 2% improvement",
                    "Outlier removal in training data helped generalization",
                    "Regularization prevented overfitting on 79 features"
                ]
            },
            "dataset_info": {
                "n_samples": 1460,
                "n_features": 79,
                "n_test": 1459,
                "missing_data": "Multiple features with varying amounts"
            }
        },
        {
            "question_id": "mle_synth_digit_recognizer",
            "question_text": """Kaggle Competition: Digit Recognizer

**Goal**: Classify handwritten digits (0-9) from MNIST dataset.

**Dataset**: 42,000 training samples, 28,000 test samples
**Features**: 784 pixel values (28x28 grayscale images)
**Target**: Digit label (0-9)

**Evaluation Metric**: Accuracy (percentage of digits correctly classified)

**Task**: Build a classifier to recognize handwritten digits.

**Difficulty**: Getting Started (Beginner)
**Competition Type**: Multi-class Classification, Computer Vision
            """,
            "domain": "Deep Learning",
            "subdomain": "Computer Vision",
            "difficulty_score": 0.25,
            "source_benchmark": "MLE-Bench (Synthetic)",
            "competition_tier": "Getting Started",
            "evaluation_metrics": ["accuracy"],
            "solution": {
                "winning_approach": "Convolutional Neural Network (CNN)",
                "key_techniques": [
                    "convolutional_layers",
                    "data_augmentation",
                    "dropout_regularization",
                    "batch_normalization"
                ],
                "model_details": {
                    "model_type": "CNN",
                    "architecture": [
                        "Conv2D(32, 3x3) -> BatchNorm -> ReLU -> MaxPool",
                        "Conv2D(64, 3x3) -> BatchNorm -> ReLU -> MaxPool",
                        "Conv2D(128, 3x3) -> BatchNorm -> ReLU -> MaxPool",
                        "Flatten",
                        "Dense(256) -> Dropout(0.5)",
                        "Dense(10, softmax)"
                    ],
                    "optimizer": "Adam",
                    "learning_rate": 0.001
                },
                "code_snippet": """
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Build CNN
model = models.Sequential([
    layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
    layers.BatchNormalization(),
    layers.MaxPooling2D((2, 2)),

    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.BatchNormalization(),
    layers.MaxPooling2D((2, 2)),

    layers.Conv2D(128, (3, 3), activation='relu'),
    layers.BatchNormalization(),
    layers.MaxPooling2D((2, 2)),

    layers.Flatten(),
    layers.Dense(256, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(10, activation='softmax')
])

# Data augmentation
datagen = ImageDataGenerator(
    rotation_range=10,
    width_shift_range=0.1,
    height_shift_range=0.1,
    zoom_range=0.1
)

# Train
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
model.fit(datagen.flow(X_train, y_train, batch_size=32), epochs=30, validation_split=0.1)
                """,
                "performance": {
                    "leaderboard_score": 0.9952,  # 99.52% accuracy
                    "cv_score": 0.9948,
                    "rank_percentile": 85
                },
                "lessons_learned": [
                    "Data augmentation crucial for preventing overfitting",
                    "Batch normalization stabilized training",
                    "Dropout regularization improved generalization",
                    "3-layer CNN sufficient for MNIST",
                    "Adam optimizer converged faster than SGD"
                ]
            },
            "dataset_info": {
                "n_samples": 42000,
                "n_features": 784,
                "n_test": 28000,
                "image_size": "28x28 pixels",
                "channels": 1
            }
        },
        {
            "question_id": "mle_synth_nlp_disaster",
            "question_text": """Kaggle Competition: NLP with Disaster Tweets

**Goal**: Predict which tweets are about real disasters vs not.

**Dataset**: 7,613 training samples, 3,263 test samples
**Features**: Tweet text, keyword, location
**Target**: Binary (1 = disaster, 0 = not disaster)

**Evaluation Metric**: F1 Score

**Task**: Build an NLP model to classify disaster-related tweets.

**Difficulty**: Getting Started (Beginner)
**Competition Type**: NLP, Binary Classification
            """,
            "domain": "Natural Language Processing",
            "subdomain": "Text Classification",
            "difficulty_score": 0.3,
            "source_benchmark": "MLE-Bench (Synthetic)",
            "competition_tier": "Getting Started",
            "evaluation_metrics": ["f1_score", "accuracy"],
            "solution": {
                "winning_approach": "BERT fine-tuning",
                "key_techniques": [
                    "transformer_models",
                    "text_preprocessing",
                    "fine_tuning",
                    "learning_rate_scheduling"
                ],
                "model_details": {
                    "model_type": "BERT (distilbert-base-uncased)",
                    "max_length": 128,
                    "batch_size": 16,
                    "epochs": 3,
                    "learning_rate": 2e-5
                },
                "code_snippet": """
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, Trainer, TrainingArguments
import torch

# Load pre-trained model
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-uncased', num_labels=2)

# Tokenize
def tokenize_function(examples):
    return tokenizer(examples['text'], padding='max_length', truncation=True, max_length=128)

tokenized_train = train_dataset.map(tokenize_function, batched=True)

# Fine-tune
training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=3,
    per_device_train_batch_size=16,
    learning_rate=2e-5,
    warmup_steps=500,
    weight_decay=0.01
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_val
)

trainer.train()
                """,
                "performance": {
                    "leaderboard_score": 0.84,  # F1 score - Top 15%
                    "cv_score": 0.83,
                    "rank_percentile": 85
                },
                "lessons_learned": [
                    "BERT significantly outperformed TF-IDF + classical ML",
                    "Text preprocessing (URL removal, @mentions) helped slightly",
                    "Learning rate scheduling crucial for stable fine-tuning",
                    "3 epochs optimal - more caused overfitting",
                    "Keyword feature added minimal value with BERT"
                ]
            },
            "dataset_info": {
                "n_samples": 7613,
                "n_features": 3,
                "n_test": 3263,
                "avg_tweet_length": "15 words"
            }
        },
        {
            "question_id": "mle_synth_time_series_sales",
            "question_text": """Kaggle Competition: Store Sales - Time Series Forecasting

**Goal**: Forecast store sales using time-series data.

**Dataset**: 3,000,888 training records, 28,512 test records
**Features**: Date, store_nbr, family (product category), onpromotion, sales
**Target**: Sales (continuous)

**Evaluation Metric**: RMSLE (Root Mean Squared Logarithmic Error)

**Task**: Build a time series model to forecast grocery store sales.

**Difficulty**: Master (Advanced)
**Competition Type**: Time Series Forecasting
            """,
            "domain": "Time Series",
            "subdomain": "Forecasting",
            "difficulty_score": 0.75,
            "source_benchmark": "MLE-Bench (Synthetic)",
            "competition_tier": "Master",
            "evaluation_metrics": ["rmsle", "rmse"],
            "solution": {
                "winning_approach": "Ensemble of LightGBM + Prophet + LSTM",
                "key_techniques": [
                    "feature_engineering_time_series",
                    "lag_features",
                    "rolling_statistics",
                    "fourier_features",
                    "model_ensembling"
                ],
                "features_engineered": [
                    "Lag features (1, 7, 14, 28 days)",
                    "Rolling mean/std (7, 14, 28 day windows)",
                    "Day of week, day of month, month, year",
                    "Holiday indicators",
                    "Promotion momentum features"
                ],
                "model_details": {
                    "model_type": "Ensemble (LightGBM + Prophet + LSTM)",
                    "ensemble_weights": [0.5, 0.3, 0.2],
                    "lgb_params": {
                        "num_leaves": 31,
                        "learning_rate": 0.05,
                        "feature_fraction": 0.8
                    }
                },
                "code_snippet": """
import lightgbm as lgb
from prophet import Prophet
from tensorflow.keras import models, layers
import numpy as np

# Feature engineering
def create_time_features(df):
    df['day_of_week'] = df['date'].dt.dayofweek
    df['day_of_month'] = df['date'].dt.day
    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year

    # Lag features
    for lag in [1, 7, 14, 28]:
        df[f'sales_lag_{lag}'] = df.groupby(['store_nbr', 'family'])['sales'].shift(lag)

    # Rolling statistics
    for window in [7, 14, 28]:
        df[f'sales_rolling_mean_{window}'] = df.groupby(['store_nbr', 'family'])['sales'].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean()
        )

    return df

# Train LightGBM
lgb_model = lgb.train(params, train_data, num_boost_round=1000)

# Train Prophet (per store-family combination)
prophet_models = {}
for store, family in store_family_combinations:
    model = Prophet(yearly_seasonality=True, weekly_seasonality=True)
    model.fit(historical_data)
    prophet_models[(store, family)] = model

# Ensemble predictions
final_predictions = (
    0.5 * lgb_predictions +
    0.3 * prophet_predictions +
    0.2 * lstm_predictions
)
                """,
                "performance": {
                    "leaderboard_score": 0.385,  # RMSLE - Top 1%
                    "cv_score": 0.392,
                    "rank_percentile": 99
                },
                "lessons_learned": [
                    "Lag features were most predictive",
                    "Prophet captured seasonality well but needed ensemble",
                    "LSTM added value for complex patterns",
                    "Store-family specific models better than global",
                    "Promotion features critical for sales spikes"
                ]
            },
            "dataset_info": {
                "n_samples": 3000888,
                "n_stores": 54,
                "n_product_families": 33,
                "date_range": "2013-2017"
            }
        }
    ]

    return competitions


def save_synthetic_mle_bench():
    """Save synthetic MLE-Bench data"""

    competitions = create_synthetic_mle_bench()

    # Save to file
    output = {
        "metadata": {
            "source": "Synthetic MLE-Bench",
            "description": "Realistic synthetic Kaggle competition questions for demonstration",
            "created_at": datetime.now().isoformat(),
            "note": "Replace with real MLE-Bench data when available",
            "total_competitions": len(competitions)
        },
        "competitions": competitions
    }

    output_path = Path("./data/synthetic_mle_bench.json")
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✅ Saved {len(competitions)} synthetic MLE-Bench competitions to {output_path}")
    print(f"\nCompetitions:")
    for comp in competitions:
        print(f"  • {comp['question_id']}: {comp['subdomain']} (difficulty: {comp['difficulty_score']:.2f})")

    return output_path


if __name__ == "__main__":
    save_synthetic_mle_bench()
