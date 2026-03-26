import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
import sys
import os

# Add the project root to the path to import nlp module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nlp.nlp_pipeline import extract_skills, extract_experience, count_skills
 

def load_resume_data(filepath):
    """
    Load the resume dataset from CSV file.
    Handles large files by reading in chunks if necessary.
    """
    try:
        # For large files, can use chunksize, but for now assume it fits
        df = pd.read_csv(filepath)
        print(f"Loaded {len(df)} resumes from {filepath}")
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def handle_missing_values(df):
    """
    Handle missing values in the dataset.
    """
    # Check for missing values
    print("Missing values before cleaning:")
    print(df.isnull().sum())

    # Drop rows with missing Resume_str or Category
    df = df.dropna(subset=['Resume_str', 'Category'])

    # Fill missing Resume_html if any, but probably not needed
    df['Resume_html'] = df['Resume_html'].fillna('')

    print(f"After cleaning, {len(df)} resumes remain")
    return df

def remove_duplicates(df):
    """
    Remove duplicate resumes based on Resume_str.
    """
    initial_count = len(df)
    df = df.drop_duplicates(subset=['Resume_str'])
    print(f"Removed {initial_count - len(df)} duplicates")
    return df

def encode_categorical_features(df):
    """
    Encode categorical features like Category.
    """
    le = LabelEncoder()
    df['Category_encoded'] = le.fit_transform(df['Category'])
    print("Encoded categories:", le.classes_)
    return df, le

def extract_basic_features(df):
    """
    Extract basic features: resume length, word count, etc.
    """
    df['resume_length'] = df['Resume_str'].apply(len)
    df['word_count'] = df['Resume_str'].apply(lambda x: len(x.split()))
    return df

def extract_advanced_features(df):
    """
    Extract advanced NLP features: skills, experience, etc.
    """
    print("[..] Extracting skills ... ", end="", flush=True)
    df['skills'] = df['Resume_str'].apply(extract_skills)
    df['skill_count'] = df['Resume_str'].apply(count_skills)
    print("done")

    print("[..] Extracting experience ... ", end="", flush=True)
    df['experience_years'] = df['Resume_str'].apply(extract_experience)
    print("done")

    return df

def scale_numerical_features(df, numerical_cols):
    """
    Scale numerical features.
    """
    scaler = StandardScaler()
    df[numerical_cols] = scaler.fit_transform(df[numerical_cols])
    return df, scaler

# Main preprocessing function
def preprocess_data(filepath):
    """
    Complete data preprocessing pipeline.
    """
    # Load data
    df = load_resume_data(filepath)
    if df is None:
        return None

    # Clean data
    df = handle_missing_values(df)
    df = remove_duplicates(df)

    # Extract features
    df = extract_basic_features(df)
    df = extract_advanced_features(df)

    # Encode categorical
    df, label_encoder = encode_categorical_features(df)

    # For now, no numerical scaling as we have basic features
    # If more numerical, add here

    return df, label_encoder