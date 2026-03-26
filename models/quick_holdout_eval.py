import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score

path = r'c:\Users\indiranivas_s\OneDrive - LevelShift\Documents\mini_project\dataset\Resume\Resume.csv'
df = pd.read_csv(path)
df = df.dropna(subset=['Resume_str', 'Category']).drop_duplicates(subset=['Resume_str'])

df['resume_length'] = df['Resume_str'].str.len()
df['word_count'] = df['Resume_str'].str.split().str.len()
df['skill_count'] = df['Resume_str'].str.count('python|java|javascript|sql|aws|azure|docker|kubernetes|flask|django|pandas|numpy').fillna(0).astype(int)
df['experience_years'] = df['Resume_str'].str.extract(r'(\\d+)\\s*\\+?\\s*year', expand=False).fillna(0).astype(int)

high_demand = ['INFORMATION-TECHNOLOGY', 'ENGINEERING', 'FINANCE']
df['shortlist'] = df['Category'].apply(lambda x: 1 if x in high_demand else 0)

# known-good subset selection
good = df[df['shortlist'] == 1]
notgood = df[df['shortlist'] == 0]
print('good', len(good), 'notgood', len(notgood))

sample_size = min(300, len(good), len(notgood))
if sample_size < 10:
    sample_size = min(100, len(df))

df_sample = pd.concat([good.sample(sample_size, random_state=42), notgood.sample(sample_size, random_state=42)])
df_sample = df_sample.sample(frac=1, random_state=42)

X_num = df_sample[['resume_length', 'word_count', 'skill_count', 'experience_years']]
vectorizer = TfidfVectorizer(max_features=300, stop_words='english', ngram_range=(1,2))
X_text = vectorizer.fit_transform(df_sample['Resume_str'].fillna(''))

X_scaled = StandardScaler().fit_transform(X_num)
import scipy.sparse as sp
X = sp.hstack((X_scaled, X_text))

y = df_sample['shortlist']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
clf.fit(X_train, y_train)

p = clf.predict(X_test)

print('acc', accuracy_score(y_test, p))
print('prec', precision_score(y_test, p))
print('recall', recall_score(y_test, p))
print('f1', f1_score(y_test, p))
print(classification_report(y_test, p, digits=4))

import joblib, os
os.makedirs('models', exist_ok=True)
joblib.dump(clf, 'models/quick_holdout_rf.pkl')
joblib.dump(vectorizer, 'models/quick_holdout_tfidf.pkl')
joblib.dump(StandardScaler().fit(X_num), 'models/quick_holdout_scaler.pkl')
