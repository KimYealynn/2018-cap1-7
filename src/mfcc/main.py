import glob
import os
import numpy as np
import sys

import scipy
import scipy.io.wavfile

from scikits.talkbox.features import mfcc

from collections import defaultdict

from sklearn.metrics import precision_recall_curve, roc_curve
from sklearn.metrics import auc
from sklearn.cross_validation import ShuffleSplit

from sklearn.metrics import confusion_matrix

from utils import plot_roc, plot_confusion_matrix, GENRE_LIST, GENRE_DIR, WAV_DIR

from ceps import read_ceps

from save import make_wav

genre_list = GENRE_LIST
genre_dir = GENRE_DIR


def train_model(clf_factory, X, Y, name, plot=False):
    labels = np.unique(Y)

    cv = ShuffleSplit(n=len(X), n_iter=1, test_size=0.3, indices=True, random_state=0)

    train_errors = []
    test_errors = []

    scores = []
    pr_scores = defaultdict(list)
    precisions, recalls, thresholds = defaultdict(
        list), defaultdict(list), defaultdict(list)

    roc_scores = defaultdict(list)
    tprs = defaultdict(list)
    fprs = defaultdict(list)

    clfs = []  # just to later get the median

    cms = []
    for train, test in cv:
        X_train, y_train = X[train], Y[train]
        X_test, y_test = X[test], Y[test]
        clf = clf_factory()

        clf.fit(X_train, y_train)
        clfs.append(clf)

        train_score = clf.score(X_train, y_train)
        test_score = clf.score(X_test, y_test)
        scores.append(test_score)

        train_errors.append(1 - train_score)
        test_errors.append(1 - test_score)

        y_pred = clf.predict(X_test)

        cm = confusion_matrix(y_test, y_pred)

        cms.append(cm)

        for label in labels:
            y_label_test = np.asarray(y_test == label, dtype=int)
            proba = clf.predict_proba(X_test)
            proba_label = proba[:, label]

            precision, recall, pr_thresholds = precision_recall_curve(
                y_label_test, proba_label)
            pr_scores[label].append(auc(recall, precision))
            precisions[label].append(precision)
            recalls[label].append(recall)
            thresholds[label].append(pr_thresholds)

            fpr, tpr, roc_thresholds = roc_curve(y_label_test, proba_label)
            roc_scores[label].append(auc(fpr, tpr))
            tprs[label].append(tpr)
            fprs[label].append(fpr)

    if plot:
        for label in labels:
            print("Plotting %s" % genre_list[label])
            scores_to_sort = roc_scores[label]
            median = np.argsort(scores_to_sort)[len(scores_to_sort) / 2]

            desc = "%s %s" % (name, genre_list[label])
      #      plot_roc(roc_scores[label][median], desc, tprs[label][median],
       #              fprs[label][median], label='%s vs rest' % genre_list[label])

    all_pr_scores = np.asarray(pr_scores.values()).flatten()
    summary = (np.mean(scores), np.std(scores),
               np.mean(all_pr_scores), np.std(all_pr_scores))
    print("%.3f\t%.3f\t%.3f\t%.3f\t" % summary)

    return np.mean(train_errors), np.mean(test_errors), np.asarray(cms), clf


def create_model():
    from sklearn.linear_model.logistic import LogisticRegression
    clf = LogisticRegression()

    return clf

def read_files(fn, genre, base_dir=genre_dir ):
    X = []
    for fn in glob.glob(os.path.join(base_dir, genre, fn)):
        ceps = np.load(fn)
        num_ceps = len(ceps)
        X.append(
            np.mean(ceps[int(num_ceps / 10):int(num_ceps * 9 / 10)], axis=0))

    return np.array(X)




def create_ceps(fn):
    sample_rate, X = scipy.io.wavfile.read(fn)

    ceps, mspec, spec = mfcc(X)

    #base_fn, ext = os.path.splitext(fn)
    #data_fn = base_fn + ".ceps"
    #np.save(data_fn, ceps)
    #print("Written %s"%data_fn)
    return ceps


if __name__ == "__main__":
    wavfile_num = 0
    wavfile_name = "file"
    X, y = read_ceps(genre_list)

    train_avg, test_avg, cms ,clfss= train_model(
        create_model, X, y, "Log Reg CEPS", plot=True)

    cm_avg = np.mean(cms, axis=0)
    cm_norm = cm_avg / np.sum(cm_avg, axis=0)

    plot_confusion_matrix(cm_norm, genre_list, "ceps",
                          "Confusion matrix of a CEPS based classifier")

    DIR = "C:\Users\lynn\PycharmProjects\\2018-cap1-7\src\mfcc"
    while wavfile_num != 10 :

        make_wav("file", wavfile_num)
        os.chdir(DIR)
        glob_wav = os.path.join(sys.argv[1], wavfile_name+str(wavfile_num)+".wav")
        print(glob_wav)
        print("-----------------------")
        for fn in glob.glob(glob_wav):
            af = create_ceps(glob_wav)
            arr_c = clfss.predict(af)
            print (arr_c)
        print("-----------------------")
        print("-----------------------")

        wavfile_num += 1
