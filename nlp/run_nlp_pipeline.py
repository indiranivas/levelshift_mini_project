import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data.data_processing import preprocess_data
from nlp.nlp_pipeline import process_dataset_nlp
import pandas as pd

def main():
    """
    Run NLP pipeline on the resume dataset.
    """
    # Load and preprocess data
    dataset_path = r"c:\Users\indiranivas_s\OneDrive - LevelShift\Documents\mini_project\dataset\Resume\Resume.csv"
    df, _ = preprocess_data(dataset_path)

    if df is None:
        print("Failed to load data.")
        return

    print("Applying NLP pipeline to dataset...")

    # Process with NLP
    features_df, nlp_pipeline = process_dataset_nlp(df)

    # Combine with original data
    df_with_features = pd.concat([df.reset_index(drop=True), features_df], axis=1)

    print(f"NLP processing completed!")
    print(f"Dataset shape: {df_with_features.shape}")
    print("Sample features:")
    print(df_with_features[['Category', 'token_count', 'unique_tokens']].head())

    # Save processed data (optional)
    # df_with_features.to_csv('data/processed_resumes_with_nlp.csv', index=False)
    # print("Processed data saved to data/processed_resumes_with_nlp.csv")

    return df_with_features, nlp_pipeline

if __name__ == "__main__":
    df_processed, pipeline = main()