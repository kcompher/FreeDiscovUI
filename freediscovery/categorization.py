# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import numpy as np
import scipy
from scipy.special import logit, expit
from sklearn.externals import joblib
from sklearn.preprocessing import LabelEncoder


from .base import _BaseWrapper
from .utils import setup_model, _rename_main_thread
from .neighbors import NearestCentroidRanker, NearestNeighborRanker
from .exceptions import (ModelNotFound, WrongParameter, NotImplementedFD, OptionalDependencyMissing)


def explain_binary_categorization(estimator, vocabulary, X_row):
    """Explain the binary categorization results

    Parameters
    ----------
    estimator : sklearn.base.BaseEstimator
      the binary categorization estimator
      (must have a `decision_function` method)
    vocabulary : list [n_features]
      vocabulary (list of words or n-grams) 
    X_row : sparse CSR ndarray [n_features]
      a row of the document term matrix
    """
    if X_row.ndim != 2 or X_row.shape[0] != 1:
        raise ValueError('X_row must be an 2D sparse array,'
                         'with shape (1, N) not {}'.format(X_row.shape))
    if X_row.shape[1] != len(vocabulary):
        raise ValueError(
                'The vocabulary length ({}) does not match '.format(len(vocabulary)) +\
                'the number of features in X_row ({})'.format(X_row.shape[1]))

    vocabulary_inv = {ind: key for key, ind in vocabulary.items()}


    if type(estimator).__name__ == 'LogisticRegression':
        coef_ = estimator.coef_
        if X_row.shape[1] != coef_.shape[1]:
            raise ValueError("Coefficients size {} does not match n_features={}".format(
                                        coef_.shape[1], X_row.shape[1]))

        indices = X_row.indices
        weights = X_row.data*estimator.coef_[0, indices]
        weights_dict = {}
        for ind, value in zip(indices, weights):
            key = vocabulary_inv[ind]
            weights_dict[key] = value
        return weights_dict
    else:
        raise NotImplementedError()


class _CategorizerWrapper(_BaseWrapper):
    """ Document categorization model

    The option `use_hashing=True` must be set for the feature extraction.
    Recommended options also include, `use_idf=1, sublinear_tf=0, binary=0`.

    Parameters
    ----------
    cache_dir : str
      folder where the model will be saved
    parent_id : str, optional
      dataset id
    mid : str, optional
      model id
    cv_scoring : str, optional, default='roc_auc'
      score that is used for Cross Validation, cf. sklearn
    cv_n_folds : str, optional
      number of K-folds used for Cross Validation
    """

    _wrapper_type = "categorizer"

    def __init__(self, cache_dir='/tmp/',  parent_id=None, mid=None,
            cv_scoring='roc_auc', cv_n_folds=3):

        super(_CategorizerWrapper, self).__init__(cache_dir=cache_dir,
                                          parent_id=parent_id,
                                          mid=mid, load_model=True)

        if mid is not None:
            self.le = joblib.load(os.path.join(self.model_dir, mid, 'label_encoder'))
        self.cv_scoring = cv_scoring
        self.cv_n_folds = cv_n_folds


    @staticmethod
    def _build_estimator(Y_train, method, cv, cv_scoring, cv_n_folds, **options):
        if cv:
            #from sklearn.cross_validation import StratifiedKFold
            #cv_obj = StratifiedKFold(n_splits=cv_n_folds, shuffle=False)
            cv_obj = cv_n_folds  # temporary hack (due to piclking issues otherwise, this needs to be fixed)
        else:
            cv_obj = None

        _rename_main_thread()

        if method == 'LinearSVC':
            from sklearn.svm import LinearSVC
            if cv is None:
                cmod = LinearSVC(**options)
            else:
                try:
                    from freediscovery_extra import make_linearsvc_cv_model
                except ImportError:
                    raise OptionalDependencyMissing('freediscovery_extra')
                cmod = make_linearsvc_cv_model(cv_obj, cv_scoring, **options)
        elif method == 'LogisticRegression':
            from sklearn.linear_model import LogisticRegression
            if cv is None:
                cmod = LogisticRegression(**options)
            else:
                try:
                    from freediscovery_extra import make_logregr_cv_model
                except ImportError:
                    raise OptionalDependencyMissing('freediscovery_extra')
                cmod = make_logregr_cv_model(cv_obj, cv_scoring, **options)
        elif method == 'NearestCentroid':
            cmod  = NearestCentroidRanker()
        elif method == 'NearestNeighbor':
            cmod = NearestNeighborRanker()
        elif method == 'xgboost':
            try:
                import xgboost as xgb
            except ImportError:
                raise OptionalDependencyMissing('xgboost')
            if cv is None:
                try:
                    from freediscovery_extra import make_xgboost_model
                except ImportError:
                    raise OptionalDependencyMissing('freediscovery_extra')
                cmod = make_xgboost_model(cv_obj, cv_scoring, **options)
            else:
                try:
                    from freediscovery_extra import make_xgboost_cv_model
                except ImportError:
                    raise OptionalDependencyMissing('freediscovery_extra')
                cmod = make_xgboost_cv_model(cv, cv_obj, cv_scoring, **options)
        elif method == 'MLPClassifier':
            if cv is not None:
                raise NotImplementedFD('CV not supported with MLPClassifier')
            from sklearn.neural_network import MLPClassifier
            cmod = MLPClassifier(solver='adam', hidden_layer_sizes=10,
                                 max_iter=200, activation='identity', verbose=0)
        else:
            raise WrongParameter('Method {} not implemented!'.format(method))
        return cmod

    def train(self, index, y, method='LinearSVC', cv=None):
        """
        Train the categorization model

        Parameters
        ----------
        index : array-like, shape (n_samples)
           document indices of the training set
        y : array-like, shape (n_samples)
           target class relative to index (string or int)
        method : str
           the ML algorithm to use (one of "LogisticRegression", "LinearSVC", 'xgboost')
        cv : str
           use cross-validation
        Returns
        -------
        cmod : sklearn.BaseEstimator
           the scikit learn classifier object
        Y_train : array-like, shape (n_samples)
           training predictions
        """

        valid_methods = ["LinearSVC", "LogisticRegression", "xgboost",
                         "NearestCentroid", "NearestNeighbor"]

        if method in ['MLPClassifier']:
            raise WrongParameter('method={} is implemented but not production ready. It was disabled for now.'.format(method))

        if method not in valid_methods:
            raise WrongParameter('method={} is not supported, should be one of {}'.format(
                method, valid_methods)) 
        if cv is not None and method in ['NearestNeighbor', 'NearestCentroid']:
            raise WrongParameter('Cross validation (cv={}) not supported with {}'.format(
                                        cv, method))

        if cv not in [None, 'fast', 'full']:
            raise WrongParameter('cv')

        d_all = self.pipeline.data

        X_train = d_all[index, :]

        Y_labels = y

        self.le = LabelEncoder()
        Y_train = self.le.fit_transform(Y_labels)

        cmod = self._build_estimator(Y_train, method, cv, self.cv_scoring, self.cv_n_folds)

        mid, mid_dir = setup_model(self.model_dir)

        if method == 'xgboost' and not cv:
            cmod.fit(X_train, Y_train, eval_metric='auc')
        else:
            cmod.fit(X_train, Y_train)



        joblib.dump(self.le, os.path.join(mid_dir, 'label_encoder'))
        joblib.dump(cmod, os.path.join(mid_dir, 'model'))

        pars = {
            'method': method,
            'index': index,
            'y': y,
            'categories': self.le.classes_
            }
        pars['options'] = cmod.get_params()
        self._pars = pars
        joblib.dump(pars, os.path.join(mid_dir, 'pars'))

        self.mid = mid
        self.cmod = cmod
        return cmod, Y_train

    def predict(self, chunk_size=5000, kind='probability'):
        """
        Predict the relevance using a previously trained model

        Parameters
        ----------
        chunck_size : int
           chunck size

        kind : str
           type of the output in ['decision_function', 'probability'], only affects ML methods. The nearest Neighbor ranker always return cosine similarities in any case.

        Returns
        -------
        res : ndarray [n_samples, n_classes]
           the score for each class
        nn_ind : {ndarray [n_samples, n_classes], None}
           the index of the nearest neighbor for each class (when the NearestNeighborRanker is used)
        """
        if kind not in ['probability', 'decision_function']:
            raise ValueError("Wrong input value kind={}, must be one of ['probability', 'decision_function']".format(kind))

        if kind == 'probability':
            kind = 'predict_proba'

        if self.cmod is not None:
            cmod = self.cmod
        else:
            raise WrongParameter('The model must be trained first, or sid must be provided to load\
                    a previously trained model!')

        ds = self.pipeline.data

        nn_ind = None
        if isinstance(cmod, NearestNeighborRanker):
            res, nn_ind = cmod.kneighbors(ds)
        elif hasattr(cmod, kind):
            res = getattr(cmod, kind)(ds)
        elif hasattr(cmod, 'decision_function'):
            # and we need predict_proba
            res = cmod.decision_function(ds)
            res = expit(res)
        elif hasattr(cmod, 'predict_proba'):
            # and we need decision_function
            res = cmod.predict_proba(ds)
            res = logit(res)
        else:
            raise ValueError('Model {} has neither decision_function nor predict_proba methods!'.format(cmod))

        # handle the case of binary categorization
        if res.ndim == 1:
            if kind == 'decision_function':
                res_p = res
                res_n = - res
            else:
                res_p = res
                res_n = 1 - res
            res = np.hstack((res_n[:,None], res_p[:, None]))
        return res, nn_ind

    @staticmethod
    def to_dict(Y_pred, nn_pred, labels, id_mapping,
                max_result_categories=1, sort=False):
        """
        Create a nested dictionary result that would be returned by 
        the REST API given the categorization results

        Parameters
        ----------
        Y_pred : ndarray [n_samples, n_categories]
           the score for each class
        nn_ind : {ndarray [n_samples, n_classes], None}
           the index of the nearest neighbor for each class (when the NearestNeighborRanker is used)
        labels : list
           list of categories label
        id_mapping : a pd.DataFrame
           the metadata mapping from freediscovery.ingestion.DocumentIndex.data
        max_result_categories : int
           the maximum number of categories in the results
        sort : bool
           sort by the score of the most likely class
        """
        if max_result_categories <= 0:
            raise ValueError('the max_result_categories={} must be strictly positive'.format(max_result_categories))

        # have to cast to object as otherwise we get serializing np.int64 issues...
        base_keys = [key for key in id_mapping.columns if key in ['internal_id',
                                                                  'document_id',
                                                                  'rendition_id']]
        id_mapping = id_mapping[base_keys].set_index('internal_id', drop=True).astype('object')

        def sort_func(x):
            return x[0]

        if nn_pred is not None:
            outer_container = zip(Y_pred.tolist(), nn_pred.tolist())
        else:
            outer_container = ((y_row, None) for y_row in Y_pred.tolist())

        res = []
        for idx, (Y_row, nn_row) in enumerate(outer_container):
            ires = {'internal_id': idx}
            ires.update(id_mapping.loc[idx].to_dict())
            iscores = []
            if nn_row is not None:
                # we have nearest neighbors results
                for Y_el, nn_el, label_el in sorted(zip(Y_row, nn_row, labels),
                                                    key=sort_func, reverse=True)[:max_result_categories]:
                    iiel = {'score': Y_el, 'internal_id': nn_el, 'category': label_el}
                    iiel.update(id_mapping.loc[idx].to_dict())
                    iscores.append(iiel)
            else:
                # no nearest neighbors available
                for Y_el, label_el in sorted(zip(Y_row, labels),
                                                    key=sort_func, reverse=True)[:max_result_categories]:
                    iiel = {'score': Y_el, 'category': label_el}
                    iscores.append(iiel)
            ires['scores'] = iscores
            res.append(ires)
        if sort:
            res = sorted(res, key=lambda x: x['scores'][0]['score'], reverse=True)
        return {'data': res}


    def _load_pars(self, mid=None):
        """Load model parameters from disk"""
        if mid is None:
            mid = self.mid
        mid_dir = os.path.join(self.model_dir, mid)
        pars = super(_CategorizerWrapper, self)._load_pars(mid)
        cmod = joblib.load(os.path.join(mid_dir, 'model'))
        pars['options'] = cmod.get_params()
        return pars
