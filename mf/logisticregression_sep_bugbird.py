import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from tqdm import tqdm
tqdm.pandas()
#%%


#%%
from utils.util import url2host

dfo = pd.read_parquet(f"data/RunBM25.1k.passages_bigbird.top_mt5")
dfo = dfo[dfo.efficacy != 0]
dfo["host"] = dfo.url.apply(url2host)
df_topic_host = dfo.groupby("topic host".split()).progress_apply(lambda x: x.loc[x.score.idxmax()])
df_topic_host = df_topic_host.reset_index(drop=True)
df_topic_host = df_topic_host.sort_values("topic score".split(), ascending=[True, False])

df_sentence_logits = pd.read_parquet("./data/run.passages_bigbird.qapubmed_sep-logits")
df_sentence_logits = df_sentence_logits.rename(columns={"sentence_scores": "sentence_score", "sentences": "sentence"})
df_sentence_logits = df_sentence_logits.merge(dfo["topic docno host".split()], on="topic docno".split(), how="inner")
df_sentence_logits = df_sentence_logits.drop(df_sentence_logits[df_sentence_logits.sentence_score.lt(0.85)].index)
#%%
xxx = df_sentence_logits.groupby("topic docno".split())
func = lambda x: x.loc[x.prob_neg.idxmax()]["prob_pos prob_may prob_neg sentence_score".split()]
# func = lambda x: pd.Series(
#     {
#         "prob_pos": ((x.sentence_score) * (x.prob_pos)).mean(),
#         "prob_may": ((x.sentence_score) * (x.prob_may)).mean(),
#         "prob_neg": ((x.sentence_score) * (x.prob_neg)).mean(),
#     })

# with Pool(2) as p:
#     ret = p.imap(func, tqdm(xxx))
#     p.join()
# xxx = pd.concat(ret)
xxx = df_sentence_logits.groupby("topic docno".split()).progress_apply(func)
xxx = xxx.reset_index()
df = df_topic_host.merge(xxx, on='topic docno'.split(), how="left")
df = df.sort_values("topic score".split(), ascending=[True, False])
df.prob_pos = df.prob_pos.fillna(0)
df.prob_neg = df.prob_neg.fillna(0)
df.prob_may = df.prob_may.fillna(1)
# df.sentence_score = df.prob_may.fillna(0)



#%%
# df["pred"] = df.apply(lambda x: np.array([x.prob_neg, x.prob_pos]).argmax(), axis=1)
# df["pred"] = df.apply(lambda x: x.prob_pos.gt(.33), axis=1)
df["pred"] = df.prob_neg.gt(.33).mul(2).add(-1).apply(lambda x: -x)
a = df[df.efficacy.eq(-1)].groupby("host").apply(lambda x: x.pred.eq(x.efficacy).astype('float').sum()).sort_values(ascending=False)
b = df[df.efficacy.eq(-1)].groupby("host").apply(lambda x: x.pred.eq(x.efficacy).astype('float').sum() * x.pred.eq(x.efficacy).astype('float').mean()).sort_values(ascending=False)
df["a_pred"] = df.progress_apply(lambda x: x.pred * a.get(x.host, 0), axis=1).fillna(0)
df["b_pred"] = df.progress_apply(lambda x: x.pred * b.get(x.host, 0), axis=1).fillna(0)
c = df.groupby("topic").apply(lambda x: pd.Series([x.b_pred.mean(), x.efficacy.max(), (x.b_pred.mean() > 0) * 2 - 1 == x.efficacy.max()]))
print(c[2].mean())
# df.pred = ((df.prob_pos* 2 -1))
# df.pred = df.pred * df.apply(lambda x: np.array([x.prob_neg, x.prob_pos]).max(), axis=1)
# df.loc[df.pred.lt(.3) & df.pred.gt(-0.3), "pred"] = 0
df.pred = df.pred.astype("float32")

# df.topic = df.topic.astype("category")
# df["topic_id"] = df.topic.cat.codes

df.host = df.host.astype("category")
df["host_id"] = df.host.cat.codes

#%%
from sklearn.linear_model import LogisticRegression

df.topic = df.topic.astype(int)
topics = df.groupby("topic").topic.max().reset_index(drop=True)
df.topic = df.topic.astype("category")
df["topic_id"] = df.topic.cat.codes

m = coo_matrix((df.b_pred, (df.topic_id, df.host_id)), shape=(df.topic_id.max() + 1, df.host_id.max()+1))
m = np.array(m.todense())
y = df[df.efficacy.ne(0)].groupby("topic").efficacy.max().clip(lower=0).to_numpy()

# df.topic = df.topic.astype(int)

train_index = topics.index[topics.astype(int).ge(1000) | topics.astype(int).le(51)]
test_index = topics.index[topics.astype(int).ge(101) & topics.astype(int).le(150)]

train_index2 = topics.index[topics.astype(int).ge(1000) | topics.astype(int).ge(101)]
test_index2 = topics.index[topics.astype(int).ge(1) & topics.astype(int).le(51)]

for train_index, test_index in [(train_index, test_index), (train_index2, test_index2)]:
    X_train = m[train_index]
    y_train = y[train_index]
    X_test = m[test_index]
    y_test = y[test_index]
    # clf = LogisticRegression(penalty='l1', solver='liblinear').fit(X_train, y_train)
    clf = Pipeline([
        # ('feature_selection', SelectFromModel(LogisticRegression(penalty='l1', solver='liblinear'))),
        # ('feature_selection', SelectFromModel(LogisticRegression(penalty='none'))),
        ('classification', LogisticRegression(penalty='l1', solver='liblinear'))
        # ('classification', LogisticRegression(penalty='elasticnet', solver='saga', l1_ratio=0.5, max_iter=200))
        # ('classification', LogisticRegression())
    ])
    clf.fit(X_train, y_train)
    print(clf.score(X_test, y_test))
# pd.DataFrame(list(zip(topics[topics.ge(1) & topics.le(51)].to_list(), clf.predict(X_test).tolist()))).merge(topics)
#%%
from sklearn.linear_model import LogisticRegression

y = df.groupby("topic").efficacy.max().clip(lower=0).to_numpy()
df.topic = df.topic.astype("category")
df["topic_id"] = df.topic.cat.codes
df = df[df.efficacy.ne(0)]
# df.pred = df.prob_pos * 2 - 1
m = coo_matrix((df.pred, (df.topic_id, df.host_id)), shape=(df.topic_id.max() + 1, df.host_id.max()+1))
m = np.array(m.todense())
kf = StratifiedKFold(n_splits=10, shuffle=False)

a = []
for train_index, test_index in kf.split(m,y):
    X_train = m[train_index]
    y_train = y[train_index]
    # y_test = df[df.efficacy.ne(0) & df.topic.ge(101)].groupby("topic").efficacy.max().clip(lower=0)
    X_test = m[test_index]
    y_test = y[test_index]
    # clf = LogisticRegression(penalty='l1', solver='liblinear').fit(X_train, y_train)
    clf = Pipeline([
        # ('feature_selection', SelectFromModel(LogisticRegression(penalty='l1', solver='liblinear'))),
        # ('classification', LogisticRegression())
        ('classification', LogisticRegression(penalty='l1', solver='liblinear')),
        # ('classification', LogisticRegression(penalty='elasticnet', solver='saga', l1_ratio=0.5, max_iter=200))
    ])
    clf.fit(X_train, y_train)
    a.append(clf.score(X_test, y_test))

print(np.mean(a))

#%%
# clf = LogisticRegression()
# clf.fit(m,y)
# a = pd.DataFrame(sorted(list(zip((np.std(m, 0)*clf.coef_)[0].tolist(),df.host.cat.categories)), key=lambda x: abs(x[0]), reverse=True))



