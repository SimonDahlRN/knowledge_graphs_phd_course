from rdflib import Graph
from rdflib import URIRef, Literal
from rdflib import Namespace
from rdflib.namespace import RDF, XSD 
from urllib import parse, request
import json
import urllib
import pandas as pd

VIN = 'VIN (1-10)'
MODEL_YEAR = 'Model Year'
MAKER = 'Make'
TYPE = 'Electric Vehicle Type'
MODEL = 'Model'
RANGE = 'Electric Range'
MSRP = 'Base MSRP' 


class CSVToKG:
    def __init__(self, csv_path, kg_path) -> None:
        self.kg_path = kg_path
        self.g = Graph()
        
        self.dbo = Namespace('http://dbpedia.org/ontology/')
        self.dbr = Namespace('http://dbpedia.org/resource/')

        self.g.bind('dbo', self.dbo)
        self.g.bind('dbr', self.dbr)

        #Remove head() to include all
        self.EV_df = pd.read_csv(csv_path, sep=',', quotechar='"',escapechar='\\').head(250) 


    def __get_URI__(self, value, query_class = None):
        url = 'https://lookup.dbpedia.org/api/search'
        params = {
            'QueryString': value,
            'MaxHits': 1,
            'format': 'json'
        }
        params.update({'QueryClass' : query_class}) if query_class else params

        url = url + '?' + parse.urlencode(params)
        req = request.Request(url)
        req.add_header('Accept', 'application/json')
        response = json.loads(request.urlopen(req).read())['docs']
        response = response[0]
        if 'resource' in response:
                for u in response['resource']:
                    #only pick the lookup if value is contained in the response
                    if value.lower() in u.lower():
                        return u

        return self.dbo+urllib.parse.quote(value.replace(' ', '_'))


    def __create_triples__(self, vin, model_year, maker, type, model, range, msrp):
        vehicle = URIRef(self.dbo+urllib.parse.quote(vin.replace(' ', '_')))
        
        ## some manufacturers are untyped (AUDI...)... - For owl#Thing and untyped resource, leave QueryClass parameter empty).
        maker = URIRef(self.__get_URI__(maker, None if maker in ['AUDI', 'TOYOTA', 'KIA', 'HONDA'] else 'Company')) 
        model = URIRef(self.__get_URI__(model, 'Automobile'))
        
        self.g.add((maker, RDF.type, self.dbo.Manufacturer))
        self.g.add((maker, self.dbo.makes, model))

        self.g.add((model, RDF.type, self.dbo.AutomobileModel))
        self.g.add((model, self.dbo.manufacturer, maker))

        self.g.add((vehicle, RDF.type, self.dbo.vehicleIdentificationNumber))
        self.g.add((vehicle, self.dbo.manufacturer, maker))
        self.g.add((vehicle, self.dbo.model, model))
        self.g.add((vehicle, self.dbo.modelYear, Literal(model_year, datatype=XSD.gYear)))
        self.g.add((vehicle, self.dbo.electricVehicleType, Literal(type, datatype=XSD.string)))
        self.g.add((vehicle, self.dbo.eletricRange, Literal(f"{range} Miles", datatype=XSD.string)))
        self.g.add((vehicle, self.dbo.baseMSRP, Literal(f"{msrp} USD", datatype=XSD.string)))
        
        
    def create_knowledge_graph(self):
        print('creating knowledge graph')
        [self.__create_triples__(vin, model_year, maker, type, model, range, msrp) for 
         vin, model_year, maker, type, model, range, msrp in 
         zip(self.EV_df[VIN], 
             self.EV_df[MODEL_YEAR], 
             self.EV_df[MAKER], 
             self.EV_df[TYPE],
             self.EV_df[MODEL], 
             self.EV_df[RANGE], 
             self.EV_df[MSRP])]

        print('saving knowledge graph')
        self.g.serialize(destination=self.kg_path, format='ttl')

        print(F"finished knowledge graph: {kg_path}")


if __name__ == '__main__':
    #Data: https://catalog.data.gov/dataset/electric-vehicle-population-data
    csv_path = 'Electric_Vehicle_Population_Data.csv'
    kg_path = 'Electric_Vehicle_Population_Data.ttl'
    g = CSVToKG(csv_path, kg_path)
    g.create_knowledge_graph()