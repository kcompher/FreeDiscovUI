# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os.path

from flask import Flask, jsonify, json
from flask.testing import FlaskClient
from flask_apispec import FlaskApiSpec

from apispec import APISpec

from .resources import (FeaturesApi, FeaturesApiElement, FeaturesApiElementMappingFlat,
                        FeaturesApiElementMappingNested,
                        ModelsApi, ModelsApiElement, ModelsApiPredict, ModelsApiTest,
                        LsiApi, LsiApiElement,
                        ClusteringApiElement, KmeanClusteringApi,
                        BirchClusteringApi, WardHCClusteringApi, DBSCANClusteringApi,
                        DupDetectionApi, DupDetectionApiElement,
                        ExampleDatasetApi,
                        MetricsCategorizationApiElement, MetricsClusteringApiElement,
                        MetricsDupDetectionApiElement,
                        EmailParserApi, EmailParserApiElementIndex,
                        EmailParserApiElement,
                        EmailThreadingApi, EmailThreadingApiElement,
                        SearchApi
                        )


#class CatchAll(Resource):
#
#    def get(self, url):
#        print("accessing", url)
#
#    def post(self, url):
#        print("accessing", url)

class TestClient(FlaskClient):
    # Addresses https://github.com/pallets/flask/issues/2176
    def open(self, *args, **kwargs):
        if 'json' in kwargs:
            kwargs['data'] = json.dumps(kwargs.pop('json'))
            kwargs['content_type'] = 'application/json'
        return super(TestClient, self).open(*args, **kwargs)


def fd_app(cache_dir):
    """ API app for FreeDiscovery """

    if not os.path.exists(cache_dir):
        raise ValueError('Cache_dir {} does not exist!'.format(cache_dir))
    app = Flask('freediscovery_api')
    app.url_map.strict_slashes = False
    app.config.update(
         {'APISPEC_SPEC': APISpec(title='FreeDiscovery',
                                  version='v0',
                                  plugins=['apispec.ext.marshmallow']),
          'APISPEC_SWAGGER_URL': '/openapi-specs.json',
          'APISPEC_SWAGGER_UI_URL': '/swagger-ui.html'})

    app.test_client_class = TestClient

    docs = FlaskApiSpec(app)

    #app.config['DEBUG'] = False


    ## Actually setup the Api resource routing here
    for resource_el, url in [
         (ExampleDatasetApi               , "/example-dataset/<name>")                             , 
         (FeaturesApi                     , "/feature-extraction")                          , 
         (FeaturesApiElement              , '/feature-extraction/<dsid>')                   , 
         (FeaturesApiElementMappingFlat   , '/feature-extraction/<dsid>/id-mapping/flat')   , 
         (FeaturesApiElementMappingNested , '/feature-extraction/<dsid>/id-mapping/nested') , 
         (EmailParserApi                  , "/email-parser")                                , 
         (EmailParserApiElement           , '/email-parser/<dsid>')                         , 
         (EmailParserApiElementIndex      , '/email-parser/<dsid>/index')                   , 
         (ModelsApi                       , '/categorization/')                             , 
         (ModelsApiElement                , '/categorization/<mid>')                        , 
         (ModelsApiPredict                , '/categorization/<mid>/predict')                , 
         (ModelsApiTest                   , "/categorization/<mid>/test")                   , 
         (LsiApi                          , '/lsi/')                                        , 
         (LsiApiElement                   , '/lsi/<mid>')                                   , 
         (KmeanClusteringApi              , '/clustering/k-mean/')                          , 
         (BirchClusteringApi              , '/clustering/birch')                            , 
         (WardHCClusteringApi             , '/clustering/ward_hc')                          , 
         (DBSCANClusteringApi             , '/clustering/dbscan')                           , 
         (ClusteringApiElement            , '/clustering/<method>/<mid>')                   , 
         (DupDetectionApi                 , '/duplicate-detection/')                        , 
         (DupDetectionApiElement          , '/duplicate-detection/<mid>')                   , 
         (MetricsCategorizationApiElement , '/metrics/categorization')                      , 
         (MetricsClusteringApiElement     , '/metrics/clustering')                          , 
         (MetricsDupDetectionApiElement   , '/metrics/duplicate-detection')                 , 
         (EmailThreadingApi               , '/email-threading/')                            , 
         (EmailThreadingApiElement        , '/email-threading/<mid>')                       , 
         (SearchApi                       , '/search/')                                     , 
         #(CatchAll                       , "/<url>")
                             ]:
        # monkeypatching, not great
        resource_el._cache_dir = cache_dir
        resource_el.methods = ['GET', 'POST', 'DELETE']
        #api.add_resource(resource_el, '/api/v0' + url, strict_slashes=False)

        ressource_name = resource_el.__name__
        app.add_url_rule('/api/v0' + url, view_func=resource_el.as_view(ressource_name))
        if ressource_name not in [ "EmailThreadingApi" ]:
            # the above two cases fail due to recursion limit
            docs.register(resource_el, endpoint=ressource_name)



    @app.errorhandler(500)
    def handle_error(error):
        #response = jsonify(error.to_dict())
        response = jsonify({'messages': str(error)})
        response.status_code = 500
        return response

    @app.errorhandler(404)
    def handle_404_error(error):
        response = jsonify({"messages": str(error)})
        response.status_code = 404 
        return response

    @app.errorhandler(400)
    def handle_400_error(error):
        response = jsonify({"messages": str(error)})
        response.status_code = 400
        return response

    @app.errorhandler(422)
    def handle_422_error(error):
        # marshmallow error
        response = jsonify(error.data)
        response.status_code = 422
        return response

    return app
