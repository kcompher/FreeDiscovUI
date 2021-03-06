# Release history

## Version 0.9

**In developpement**

### New features  



### Enhancements
 * Support for multi-class categorization (PR [#96](https://github.com/FreeDiscovery/FreeDiscovery/pull/96/files)) 

 * The REST API documentation is generated automatically from the code (using an OpenAPI specification) which allows to enforce consistency between the code and the docs (PR [#85](https://github.com/FreeDiscovery/FreeDiscovery/pull/85))
 


### API Changes
 
 * The following endpoints accepting a request body are modified from `GET` to `POST` method (PR [#94](https://github.com/FreeDiscovery/FreeDiscovery/pull/94)), in accordance with the HTTP/1.1 spec, section 4.3,
    - `/api/v0/metrics/categorization`
    - `/api/v0/metrics/clustering`
    - `/api/v0/metrics/duplicate-detection`
    - `/api/v0/feature-extraction/{dsid}/id-mapping/flat`
    - `/api/v0/feature-extraction/{dsid}/id-mapping/nested`
    - `/api/v0/email-parser/{dsid}/index`
  * Significant changes in the REST API to accomodate for multi-class categorization 
  * The `internal_id` field is not longer exposed, document are indexed with `document_id`, `rendition_id` keys.

## Version 0.8

**Feb. 25, 2017**

### New features  

 * NearestNeighbor search now can perform categorization both with positive/negative training documents (supervised) as well as with only a list of positive documents (unsupervised) (PR [#50](https://github.com/FreeDiscovery/FreeDiscovery/pull/50))
 * Document search and semantic search (PR [#63](https://github.com/FreeDiscovery/FreeDiscovery/pull/63))


### Enhancements
 
 * In depth code reorganisation making each processing step a separate REST endpoint (PR [#57](https://github.com/FreeDiscovery/FreeDiscovery/pull/57))
 * More rubust default parameters (PR [#65](https://github.com/FreeDiscovery/FreeDiscovery/pull/65))

### API Changes
 
 * Ability to associate external `document_id`, `rendition_id` fields when ingesting documents; document categorization can now be used with these external ids. 
 * All the wrappers classes are made private in the Python API
 * The same categorization and clustering enpoints can operate ether in the document-term space or in the LSI space (PR [#57](https://github.com/FreeDiscovery/FreeDiscovery/pull/57))
