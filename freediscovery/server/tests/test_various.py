# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import pytest
import json
import itertools
from unittest import SkipTest
from numpy.testing import assert_equal, assert_almost_equal

from .. import fd_app
from ...utils import _silent, dict2type, sdict_keys
from ...ingestion import DocumentIndex
from ...exceptions import OptionalDependencyMissing
from ...tests.run_suite import check_cache

from .base import parse_res, V01, app, app_notest, get_features, get_features_lsi


@pytest.mark.parametrize("method", ['regular', 'semantic'])
def test_search(app, method):

    if method == 'regular':
        dsid, lsi_id, _ = get_features_lsi(app, hashed=False)
        parent_id = lsi_id
    elif method == 'semantic':
        dsid, _ = get_features(app, hashed=False)
        lsi_id = None
        parent_id = dsid

    method = V01 + "/search/"
    res = app.post(method, json=dict(parent_id=parent_id, query="so that I can reserve a room"))
    assert res.status_code == 200
    data = parse_res(res)
    assert sorted(data.keys()) == ['data']
    for row in data['data']:
        assert sorted(row.keys()) == sorted(['score', 'internal_id'])

def test_example_dataset(app):
    res = app.get(V01 + '/example-dataset/20newsgroups_micro')
    data = parse_res(res)
    assert dict2type(data, max_depth=1) == {'dataset': 'list',
                                            'training_set': 'list',
                                            'metadata': 'dict'}
    assert dict2type(data['metadata']) == {'data_dir': 'str',
                                           'name': 'str'}
    assert dict2type(data['training_set'][0]) == {'category': 'str',
                                               'document_id': 'int',
                                               'internal_id': 'int',
                                               'file_path': 'str'}
    assert dict2type(data['dataset'][0]) == {'category': 'str',
                                           'document_id': 'int',
                                           'internal_id': 'int',
                                           'file_path': 'str'
                                          }



def test_openapi_specs(app):
    res = app.get('/openapi-specs.json')
    data = parse_res(res)
    assert data['swagger'] == '2.0'

