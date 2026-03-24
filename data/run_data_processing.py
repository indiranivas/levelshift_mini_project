from data_processing import preprocess_data

# Path to the dataset
dataset_path = r"c:\Users\indiranivas_s\OneDrive - LevelShift\Documents\mini_project\dataset\Resume\Resume.csv"

# Preprocess the data
df, label_encoder = preprocess_data(dataset_path)

if df is not None:
    print("Data preprocessing completed successfully!")
    print(f"Dataset shape: {df.shape}")
    print("Columns:", df.columns.tolist())
    print("Sample categories:", df['Category'].value_counts().head())
else:
    print("Failed to preprocess data.")