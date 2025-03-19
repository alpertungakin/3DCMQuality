# -*- coding: utf-8 -*-
"""
Created on Tue May 14 10:09:09 2024

@author: alper
"""

from pyshacl import validate
from rdflib import Graph, Literal, RDF, URIRef
from rdflib.namespace import NamespaceManager, CSVW, DC, DCAT, DCTERMS, DOAP, FOAF, GEO, ODRL2, ORG, OWL, \
                           PROF, PROV, RDF, RDFS, SDO, SH, SKOS, SOSA, SSN, TIME, \
                           VOID, XMLNS, XSD
                           
data_graph = Graph()
data_graph.parse("rotterdam_rdf.ttl", format='turtle')

shacl_graph = Graph()
shacl_graph.parse("shacl4cg_v2.ttl", format='turtle')
r = validate(data_graph,
      shacl_graph=shacl_graph,
      ont_graph=None,
      inference='rdfs',
      abort_on_first=False,
      allow_infos=False,
      allow_warnings=False,
      meta_shacl=False,
      advanced=False,
      js=False,
      debug=False)

validity, results_graph, results_text = r

val = open("validation_results.txt", "w")
val.write(results_text)
val.close()