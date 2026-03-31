import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib


# Import data processing
import sys
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
print('train_model root path:', ROOT)
print('sys.path before:', sys.path[:3])
sys.path.insert(0, ROOT)
print('sys.path after:', sys.path[:3])
from data.data_processing import preprocess_data

def create_binary_target(df):
    """
    Create a binary target for shortlist/reject.
    For demo, shortlist if category is IT, Engineering, or Finance.
    """
    high_demand_categories = ['INFORMATION-TECHNOLOGY', 'ENGINEERING', 'FINANCE']
    df['shortlist'] = df['Category'].apply(lambda x: 1 if x in high_demand_categories else 0)
    return df

def prepare_features_and_target(df):
    """
    Prepare features and target for ML.
    """
    # Features: resume_length, word_count, skill_count, experience_years
    # Removed 'Category_encoded' to prevent data leakage (100% artificial accuracy)
    features = ['resume_length', 'word_count', 'skill_count', 'experience_years']
    X = df[features]
    y = df['shortlist']
    return X, y

def train_and_evaluate_model(X, y, model, model_name):
    """
    Train and evaluate a single model.
    """
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_pred_proba = None
    if hasattr(model, 'predict_proba'):
        y_pred_proba = model.predict_proba(X_test)[:, 1]
    elif hasattr(model, 'decision_function'):
        y_pred_proba = model.decision_function(X_test)

    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred),
        'roc_auc': roc_auc_score(y_test, y_pred_proba) if y_pred_proba is not None else None
    }

    print(f"\n{model_name} Results:")
    for metric, value in metrics.items():
        if value is not None:
            print(f"{metric}: {value:.4f}")

    return model, metrics


def build_ensemble_model(tuned_models):
    """Build a hard-voting ensemble from tuned component models."""
    estimators = []
    for name, m in tuned_models.items():
        estimators.append((name.replace(' ', '_'), m))

    ensemble = VotingClassifier(estimators=estimators, voting='soft', n_jobs=-1)
    return ensemble


def evaluate_ensemble(X, y, ensemble):
    """Train and evaluate voting ensemble model with cross-validation."""
    return perform_cross_validation(X, y, ensemble, 'Voting Ensemble')


def perform_cross_validation(X, y, model, model_name):
    """
    Perform cross-validation.
    """
    scores = cross_val_score(model, X, y, cv=3, scoring='f1')
    print(f"\n{model_name} Cross-Validation F1 Scores: {scores}")
    print(f"Mean F1: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")
    return scores

def hyperparameter_tuning(X, y, model, param_grid, model_name):
    """
    Perform GridSearchCV for hyperparameter tuning.
    """
    grid_search = GridSearchCV(model, param_grid, cv=3, scoring='f1', n_jobs=1)
    grid_search.fit(X, y)

    print(f"\n{model_name} Best Parameters: {grid_search.best_params_}")
    print(f"Best F1 Score: {grid_search.best_score_:.4f}")

    return grid_search.best_estimator_

def evaluate_on_holdout(X, y, model):
    """Evaluate model on a held-out subset and print confusion and metrics."""
    from sklearn.metrics import confusion_matrix, classification_report

    X_train, X_holdout, y_train, y_holdout = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model.fit(X_train, y_train)
    y_pred_holdout = model.predict(X_holdout)

    print("\nHoldout set evaluation:")
    print("Confusion matrix:")
    print(confusion_matrix(y_holdout, y_pred_holdout))
    print("Classification report:")
    print(classification_report(y_holdout, y_pred_holdout, digits=4))

    return confusion_matrix(y_holdout, y_pred_holdout), classification_report(y_holdout, y_pred_holdout)


def save_model(model, filename):
    """
    Save the trained model using joblib.
    """
    os.makedirs('models', exist_ok=True)
    filepath = os.path.join('models', filename)
    joblib.dump(model, filepath)
    print(f"Model saved to {filepath}")

def main():
    """
    Main function to train ML models.
    """
    # Load and preprocess data
    dataset_path = os.path.join(ROOT, "dataset", "Resume", "Resume.csv")
    df, _ = preprocess_data(dataset_path)

    if df is None:
        print("Failed to load data.")
        return

    # Create binary target
    df = create_binary_target(df)

    # Prepare features and target
    X, y = prepare_features_and_target(df)

    print(f"Dataset shape: {X.shape}")
    print(f"Target distribution: {y.value_counts()}")
    
    # Fit and save global TF-IDF vectorizer for accurate cosine matching later
    print("\nFitting global TF-IDF vectorizer on all resumes...")
    tfidf = TfidfVectorizer(max_features=300, stop_words='english', ngram_range=(1, 2))
    tfidf_matrix = tfidf.fit_transform(df['Resume_str'].fillna(''))
    os.makedirs('models', exist_ok=True)
    joblib.dump(tfidf, os.path.join('models', 'tfidf_vectorizer.pkl'))
    print("Saved global TF-IDF vectorizer to models/tfidf_vectorizer.pkl")

    # Scale numerical features
    from sklearn.preprocessing import StandardScaler
    import scipy.sparse as sp
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    joblib.dump(scaler, os.path.join('models', 'standard_scaler.pkl'))
    print("Saved standard scaler to models/standard_scaler.pkl")
    
    # Combine features
    X = sp.hstack((X_scaled, tfidf_matrix))
    print(f"Final feature matrix shape: {X.shape}")

    # Define models
    models = {
        'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000),
        'Decision Tree': DecisionTreeClassifier(random_state=42),
        'Random Forest': RandomForestClassifier(random_state=42),
    }

    # Param grids for GridSearch
    param_grids = {
        'Logistic Regression': {'C': [0.1, 1]},
        'Decision Tree': {'max_depth': [5, 10], 'min_samples_split': [2, 5]},
        'Random Forest': {'n_estimators': [50], 'max_depth': [10, None]},
    }

    best_models = {}

    for model_name, model in models.items():
        # Cross-validation
        perform_cross_validation(X, y, model, model_name)

        # Hyperparameter tuning
        best_model = hyperparameter_tuning(X, y, model, param_grids[model_name], model_name)

        # Train and evaluate best model
        trained_model, metrics = train_and_evaluate_model(X, y, best_model, f"{model_name} (Tuned)")

        best_models[model_name] = trained_model

        # Save model
        save_model(trained_model, f"{model_name.lower().replace(' ', '_')}_model.pkl")

    # Build and evaluate ensemble model
    ensemble = build_ensemble_model(best_models)
    evaluate_ensemble(X, y, ensemble)

    # Optional: hold-out evaluation on best ensemble
    evaluate_on_holdout(X, y, ensemble)

    ensemble.fit(X, y)
    save_model(ensemble, 'ensemble_model.pkl')

    print("\nAll models trained and saved successfully!")

if __name__ == "__main__":
    main()
