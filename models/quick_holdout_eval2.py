import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score
import scipy.sparse as sp

path = 'dataset/Resume/Resume.csv'
print('Loading', path)
df = pd.read_csv(path)
print('Rows', len(df))

df = df.dropna(subset=['Resume_str', 'Category']).drop_duplicates(subset=['Resume_str'])
print('After clean', len(df))

df['resume_length'] = df['Resume_str'].str.len()
df['word_count'] = df['Resume_str'].str.split().str.len()
df['skill_count'] = df['Resume_str'].str.count('python|java|javascript|sql|aws|azure|docker|kubernetes|flask|django|pandas|numpy').fillna(0).astype(int)
df['experience_years'] = df['Resume_str'].str.extract(r"(\\d+)\\s*\\+?\\s*year", expand=False).fillna(0).astype(int)

high = ['INFORMATION-TECHNOLOGY', 'ENGINEERING', 'FINANCE']
df['shortlist'] = df['Category'].apply(lambda x: 1 if x in high else 0)

print('High demand records', df['shortlist'].sum(), 'others', len(df) - df['shortlist'].sum())

s = min(300, int(df['shortlist'].sum()), int(len(df) - df['shortlist'].sum()))
if s < 20:
    s = min(100, len(df))

print('Sample size per class', s)

good = df[df['shortlist'] == 1].sample(s, random_state=42)
notgood = df[df['shortlist'] == 0].sample(s, random_state=42)

df_sample = pd.concat([good, notgood]).sample(frac=1, random_state=42)

X_num = df_sample[['resume_length', 'word_count', 'skill_count', 'experience_years']]

vec = TfidfVectorizer(max_features=300, stop_words='english', ngram_range=(1,2))
X_text = vec.fit_transform(df_sample['Resume_str'].fillna(''))

X_scaled = StandardScaler().fit_transform(X_num)
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
joblib.dump(vec, 'models/quick_holdout_tfidf.pkl')
joblib.dump(StandardScaler().fit(X_num), 'models/quick_holdout_scaler.pkl')
print('Saved quick holdout models')
