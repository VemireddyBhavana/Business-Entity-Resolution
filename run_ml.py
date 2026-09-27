import pandas as pd
import re
import joblib
from rapidfuzz import fuzz
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

def clean_text(t):
    if pd.isna(t):
        return ''
    t = t.lower()
    t = re.sub(r'[^\w\s]', '', t)
    return ' '.join(t.split())

def name_sim(a, b):  return fuzz.ratio(a, b)
def addr_sim(a, b):  return fuzz.ratio(a, b)
def c_match(a, b):   return 1 if a == b else 0

print('[1/7] Loading data...')
s1 = pd.read_csv('dataset/train/train_source1.tsv', sep='\t').set_index('entity_id')
s3 = pd.read_csv('dataset/train/train_source3.tsv', sep='\t').set_index('entity_id')
gt = pd.read_csv('dataset/train/train_ground_truth.tsv', sep='\t').dropna().head(1000)

print('[2/7] Positive pairs...')
pos = []
for _, row in gt.iterrows():
    sid = row.iloc[0]
    for mid in row.iloc[1].split(','):
        if mid.startswith('S3-') and mid in s3.index and sid in s1.index:
            b1 = s1.loc[sid]
            b2 = s3.loc[mid]
            pos.append({
                'name_similarity':    name_sim(clean_text(b1['business_name']),    clean_text(b2['business_name'])),
                'address_similarity': addr_sim(clean_text(b1['business_address']), clean_text(b2['business_address'])),
                'country_match':      c_match(b1['country'], b2['country']),
                'label': 1
            })
            break

print('[3/7] Negative pairs...')
N   = len(pos)
s1n = s1.sample(n=N, random_state=42)
s3n = s3.sample(n=N, random_state=99)
neg = []
for i in range(N):
    b1 = s1n.iloc[i]
    b2 = s3n.iloc[i]
    neg.append({
        'name_similarity':    name_sim(clean_text(b1['business_name']),    clean_text(b2['business_name'])),
        'address_similarity': addr_sim(clean_text(b1['business_address']), clean_text(b2['business_address'])),
        'country_match':      c_match(b1['country'], b2['country']),
        'label': 0
    })

df = pd.concat([pd.DataFrame(pos), pd.DataFrame(neg)]).sample(frac=1, random_state=42).reset_index(drop=True)

print('[4/7] Train/Test Split...')
X = df[['name_similarity', 'address_similarity', 'country_match']]
y = df['label']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print('X_train=%s  X_test=%s' % (str(X_train.shape), str(X_test.shape)))

print('[5/7] Training RandomForest...')
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
predictions = model.predict(X_test)

print('[6/7] Evaluation...')
acc = accuracy_score(y_test, predictions)
print()
print('=' * 50)
print('  ACCURACY')
print('  %.2f%%' % (acc * 100))
print('=' * 50)

print()
print('  CONFUSION MATRIX')
cm = confusion_matrix(y_test, predictions)
print(cm)
print()
print('  What it means:')
print('  TN=%d  FP=%d' % (cm[0][0], cm[0][1]))
print('  FN=%d  TP=%d' % (cm[1][0], cm[1][1]))

print()
print('  CLASSIFICATION REPORT')
print(classification_report(y_test, predictions, target_names=['Not Match (0)', 'Match (1)']))

print('[7/7] Saving model...')
joblib.dump(model, 'models/entity_resolution_model.pkl')
print('Model saved to models/entity_resolution_model.pkl')
print()
print('Done! Module 6 complete.')