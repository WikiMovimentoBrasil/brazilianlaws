from lxml import etree
import requests
import re
import os
import json
import collections
import textwrap
from urllib.parse import quote, quote_plus
from flask_babel import gettext
from flask import current_app
from datetime import datetime

# Namespaces used in the API results
ns = {
    'srw_dc': 'info:srw/schema/1/dc-schema',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'srw': 'http://www.loc.gov/zing/srw/',
    'xsi': 'http://www.w3.org/2001/XMLSchema'
}

# Atributes used in the results
attributes = ('facet-tipoDocumento',
              'facet-localidade',
              'facet-autoridade',
              'subject',
              'date',
              'urn',
              'title',
              'description',
              'identifier')

wikidata_prop = {
    "facet-tipoDocumento": "P31",
    "date": "P577",
    "urn": "P9119",
    "facet-localidade": "P1001",
    "facet-autoridade": "P790",
    "title": "P1476",
    "description": "EMENTA",
    "subject": "P921"
}


# The script uses two classes to store the information scrapped from the LeXML api
class Law:
    """This class stores data about legislation entities"""

    def __init__(self,
                 date='',
                 urn='',
                 title='',
                 description='',
                 facet_tipoDocumento=None,
                 facet_localidade=None,
                 facet_autoridade=None,
                 subject=None,
                 qid=None,
                 country=[{"wikidatified": True, "qid": "Q155"}],
                 lang=[{"wikidatified": True, "qid": "Q750553"}],
                 wikiproject=[{"wikidatified": True, "qid": "Q105091640"}]):
        """Initial class to store the data about legislation entities

        Attributes
        ----------
        facet_tipoDocumento: str
            type of legislation
        date: str
            date of promulgation
        urn: str
            identifier of the legislation item in the database
        localidade: str
            locality where the legislation has authority
        autoridade: str
            entity that issued the legislation
        title: str
            official name of the legislation
        description: str
            legislation long title, or digest, summarizing the content of the legislation
        identifier: str
            unique identifier in the database
        subject: list
            keywords of the legislation
        """

        self.date = date
        self.urn = urn
        self.title = title
        self.description = description
        self.subject = subject or []
        self.facet_autoridade = facet_autoridade or []
        self.facet_localidade = facet_localidade or []
        self.facet_tipoDocumento = facet_tipoDocumento or []
        self.country = country
        self.lang = lang
        self.wikiproject = wikiproject
        self.qid = qid

    def wikidatify_self(self):
        """
        Function to wikidatify a Law item
        """
        return {"tipoDocumento": wikidatify_list(self.facet_tipoDocumento, 'type.json'),
                "date": _date(self.date),
                "urn": self.urn,
                "localidade": wikidatify_list(self.facet_localidade, 'locality.json'),
                "autoridade": wikidatify_list(self.facet_autoridade, 'authority.json'),
                "title": self.title,
                "description": self.description,
                "subject": wikidatify_list(self.subject, 'subject.json'),
                "country": self.country,
                "lang": self.lang,
                "wikiproject": self.wikiproject,
                "qid": self.qid}

    def create_api_self(self):
        data = {}
        claims = []

        if self.title:
            data["labels"] = labels(self.title, 'pt-br')
        if self.facet_localidade and self.facet_tipoDocumento:
            data["descriptions"] = descriptions(
                get_label(wikidatify_list([self.facet_tipoDocumento[0]], 'type.json')[0]["qid"]) +
                " com jurisdição em " +
                get_label(wikidatify_list([self.facet_localidade[0]], 'locality.json')[0]["qid"]),
                "pt-br")

        if self.facet_tipoDocumento:
            claims = claims + claim_qid(wikidatify_list(self.facet_tipoDocumento, 'type.json'), 'P31')
        if self.facet_localidade:
            claims = claims + claim_qid(wikidatify_list(self.facet_localidade, 'locality.json'), 'P1001')
        if self.facet_autoridade:
            claims = claims + claim_qid(wikidatify_list(self.facet_autoridade, 'authority.json'), 'P790')
        if self.subject:
            claims = claims + claim_qid(wikidatify_list(self.subject, 'subject.json'), 'P921')
        if self.country:
            claims = claims + claim_qid([self.country], 'P17')
        if self.lang:
            claims = claims + claim_qid([self.country], 'P407')
        if self.wikiproject:
            claims = claims + claim_qid([self.wikiproject], 'P5008')
        if self.date:
            claims = claims + claim_date(self.date, 'P577')
        if self.urn:
            claims = claims + claim_string(self.urn, 'P9119', False)
        if self.title:
            claims = claims + claim_monolingual(self.title, 'P1476')
        if self.description:
            claims = claims + claim_monolingual(self.description, 'P9376')

        if claims:
            data["claims"] = claims

        return data

    def qs_self(self):
        if self.facet_localidade and self.facet_tipoDocumento:
            dptbr = build_qs_command_string(
                get_label(wikidatify_list([self.facet_tipoDocumento[0]], 'type.json')[0]["qid"]) +
                " com jurisdição em " +
                get_label(wikidatify_list([self.facet_localidade[0]], 'locality.json')[0]["qid"]), "Dpt-br")
        else:
            dptbr = ''

        qs = ("CREATE" +
              build_qs_command_qid(wikidatify_list(self.facet_tipoDocumento, 'type.json'), 'P31') +
              build_qs_command_qid(wikidatify_list(self.facet_localidade, 'locality.json'), 'P1001') +
              build_qs_command_qid(wikidatify_list(self.facet_autoridade, 'authority.json'), 'P790') +
              build_qs_command_qid(wikidatify_list(self.subject, 'subject.json'), 'P921', False) +
              build_qs_command_qid(self.country, 'P17') +
              build_qs_command_qid(self.lang, 'P407') +
              build_qs_command_qid(self.wikiproject, 'P5008') +
              dptbr +
              build_qs_command_date(_date(self.date), 'P577') +
              build_qs_command_string(self.urn, 'P9119') +
              build_qs_command_string(self.title, 'Lpt-br') +
              build_qs_command_string(self.title, 'P1476') +
              build_qs_command_digest(self.description, 'P9376'))

        if self.qid:
            return qs[6:].replace("LAST", self.qid)
        else:
            return qs

    def print_self(self):
        """
         Function that returns the data separated by a '*' character
        """
        return (wikidatify_list(self.facet_tipoDocumento, 'type.json') + '*' +
                wikidatify_list(self.facet_autoridade, 'authority.json') + '*' +
                wikidatify_list(self.facet_localidade, 'locality.json') + '*' +
                self.date + '*' +
                self.urn + '*' +
                self.title + '*' +
                self.description + '*' +
                self.identifier + '*' +
                wikidatify_list(self.subject, 'subject.json') +
                '\n')


class Lexicon:
    """Used for keeping track of how many times each legislation subject (keyword) was used"""

    def __init__(self, word='', count=0):
        """Initial class to store data about the lexicon

        Attributes
        ----------
        word: str
            term of the lexicon
        count: int
            number of occurences of the term
        """

        self.word = word
        self.count = count


def wikidatify_list(id_list, filename):
    app = current_app
    result = []
    with open(os.path.join(app.static_folder, filename), encoding="utf-8") as queries:
        values = json.load(queries)
        for id_ in id_list:
            value = id_.replace(" ", " ")
            if value in values:
                result.append({"qid": values[value],
                               "label": value,
                               "wikidatified": True})
            else:
                result.append({"qid": None,
                               "label": value,
                               "wikidatified": False})
        return result


def get_label(qid):
    if qid:
        url = "https://query.wikidata.org/sparql"
        params = {
            "query": "SELECT ?itemLabel WHERE { SERVICE wikibase:label { bd:serviceParam wikibase:language 'pt-br,pt,en'. } BIND(wd:" + qid + " AS ?item)}",
            "format": "json"
        }
        result = requests.get(url=url, params=params, headers={'User-agent': 'WikiProject Brazilian Laws 1.0'})
        data = result.json()
        return data["results"]["bindings"][0]["itemLabel"]["value"]
    else:
        return ""


def _date(value):
    return "+" + value + "T00:00:00Z/11"


def build_qs_command_qid(parts, prop, ref=True):
    result = []
    today = datetime.today().strftime('+%Y-%m-%dT00:00:00Z/11')
    if ref:
        reference = '|S248|Q10317762|S813|' + today
    else:
        reference = ''
    for item in parts:
        if item["wikidatified"]:
            result.append(quote('||LAST|' + prop + '|' + item["qid"] + reference, safe=''))
    return "".join(result)


def build_qs_command_digest(text, prop):
    today = datetime.today().strftime('+%Y-%m-%dT00:00:00Z/11')
    ref = '|S248|Q10317762|S813|' + today
    lang = 'pt-br:'
    result = []
    if prop == 'P9376':
        parts = textwrap.wrap(text, 1500, break_long_words=False, break_on_hyphens=False)

        if parts.__len__() > 1:
            for order, part in enumerate(parts):
                qual = '|P1545|"' + str(order + 1) + '"|P1480|Q105642994'
                result.append(quote('||LAST|' + prop + '|' + lang + '"' + part + '"' + qual + ref, safe=":"))
        elif parts.__len__() == 1:
            result.append(quote('||LAST|' + prop + '|' + lang + '"' + parts[0] + '"' + ref, safe=":"))
    return "".join(result)


def build_qs_command_string(part, prop):
    if part:
        today = datetime.today().strftime('+%Y-%m-%dT00:00:00Z/11')
        if prop[:1] == "L" or prop[:1] == "D":
            ref = ''
        else:
            ref = '|S248|Q10317762|S813|' + today
        lang = 'pt-br:' if prop == 'P1476' else ''

        if part[0] == " ":
            return ""
        else:
            return quote('||LAST|' + prop + '|' + lang + '"' + part + '"' + ref, safe=":")
    else:
        return ""


def build_qs_command_date(part, prop):
    today = datetime.today().strftime('+%Y-%m-%dT00:00:00Z/11')
    if re.match(r'\+\d{4}-\d{2}-\d{2}T00:00:00Z\/11', part):
        return quote('||LAST|' + prop + '|' + part + '|S248|Q10317762|S813|' + today, safe='')
    else:
        return ""


def get_values(item):
    """Get the content of the tags for an item returned by the API

    Parameters
    ----------
    item : _Element
        item returned by the API, read as a xml.etree.ElementTree

    Returns
    ----------
    Law
        Law object with the information of a legislation item
    """

    new_law = Law()

    # Sometimes, there is more than one value for document type, locality, authority, so we
    # create a list to store the values
    types = []
    localities = []
    authorities = []

    for attr in item.iter():
        tag = attr.tag

        # Some tags present a prefix namespace, so we strip them to get the proper name of the tag
        if '}' in tag:
            tag = tag.split('}')[1]

        # We only want the information of the defined tags, everything else is ignored
        if tag in attributes:
            if tag == 'facet-tipoDocumento' and attr.text:
                attr.text = attr.text.replace('\n', '')
                types.append(attr.text)
            elif tag == 'facet-localidade' and attr.text:
                attr.text = attr.text.replace('\n', '')
                localities.append(attr.text)
            elif tag == 'facet-autoridade' and attr.text:
                attr.text = attr.text.replace('\n', '')
                authorities.append(attr.text)
            elif tag != 'subject':
                if attr.text:
                    attr.text = attr.text.replace('\n', '')
                    setattr(new_law, tag.replace("-", "_"), attr.text)
            else:
                subjects_text = re.sub(r"{[^}]+}", lambda x: x.group().replace(',', '@COMMA@'), attr.text)
                subjects = [keyword.strip().replace("@COMMA@", ",").replace("{", "").replace("}", "") for keyword in
                            re.split(r'(?:[,.]\s|\s[,.]\s)', subjects_text)]
                unique_subjects = list(set(subjects))

                # Strip unnecessary ' .' in the end of the subjects, usually present in the last keywords
                for i in range(0, len(unique_subjects)):
                    if ' .' in unique_subjects[i]:
                        unique_subjects[i] = unique_subjects[i][:-2]
                setattr(new_law, tag, unique_subjects)
    setattr(new_law, "facet_autoridade", authorities)
    setattr(new_law, "facet_localidade", localities)
    setattr(new_law, "facet_tipoDocumento", types)
    return new_law


def get_lexicon(law_item):
    lex = []

    for keyword in law_item.subject:
        lex.append(keyword)
    lexicon = collections.Counter(lex)
    lexicon = sorted(lexicon.items(), key=lambda _lex: lex[0], reverse=True)
    return lexicon


def call_api(search_terms):
    base_url = 'https://www.lexml.gov.br/busca/SRU?operation=searchRetrieve&maximumRecords=1&query=urn+='
    request_api = requests.get(base_url + '"' + search_terms + '"')
    request_api.encoding = 'utf-8'
    tree = etree.fromstring(request_api.content)

    message = ""
    status = True
    new_law = Law()
    try:
        tag = tree.findall('.//srw_dc:dc', namespaces=ns)[0]
        new_law = get_values(tag)
    except IndexError:
        message = gettext(
            u"It was not possible to find information about this item, try again removing part of the end of the URL. If it continues, please, report.")
        status = False

    lexicon = get_lexicon(new_law)
    if not new_law.urn:
        message = gettext(
            u"It was not possible to find information about this item, try again removing part of the end of the URL. If it continues, please, report.")
        status = False
    return new_law, lexicon, message, status


def check_lexml_id_in_wikidata(lexml_id):
    url = "https://query.wikidata.org/sparql"
    params = {
        "query": "SELECT ?qid (SAMPLE(?tipoDocumento) AS ?facet_tipoDocumento) (SAMPLE(?title) AS ?title) (SAMPLE(?date) AS ?date) (SAMPLE(?urn) AS ?urn) (SAMPLE(?locality) AS ?facet_localidade) (SAMPLE(?authority) AS ?facet_autoridade) (GROUP_CONCAT(?subject_;SEPARATOR=';') AS ?subject) (GROUP_CONCAT(?digest_;SEPARATOR=' ') AS ?description) WHERE { ?item wdt:P9119 '" + lexml_id + "'. BIND(SUBSTR(STR(?item),32) AS ?qid) OPTIONAL{ ?item wdt:P31 ?tipoDocumento_. BIND(SUBSTR(STR(?tipoDocumento_),32) AS ?tipoDocumento)} OPTIONAL{ ?item wdt:P1476 ?title. } OPTIONAL{ ?item p:P577/psv:P577 ?date_p. ?date_p wikibase:timeValue ?date_wb. ?date_p wikibase:timePrecision ?date_precision. BIND(CONCAT('+',STR(?date_wb),'/',STR(?date_precision)) AS ?date) } OPTIONAL{ ?item wdt:P9119 ?urn. } OPTIONAL{ ?item wdt:P1001 ?locality_. BIND(SUBSTR(STR(?locality_),32) AS ?locality) } OPTIONAL{ ?item wdt:P790 ?authority_. BIND(SUBSTR(STR(?authority_),32) AS ?authority) } OPTIONAL{ ?item wdt:P921 ?subject_aux. BIND(SUBSTR(STR(?subject_aux),32) AS ?subject_) } OPTIONAL{ ?item wdt:P9376 ?digest_. FILTER(LANG(?digest_)='pt-br') } } GROUP BY ?qid",
        "format": "json"
    }
    result = requests.get(url=url, params=params, headers={'User-agent': 'WikiProject Brazilian Laws 1.0'})
    data = result.json()
    return data["results"]["bindings"]


def post_search_entity(term, lang="pt-br"):
    url = 'https://www.wikidata.org/w/api.php'
    params = {
        'action': 'wbsearchentities',
        'search': term,
        'language': lang,
        'format': 'json',
        'limit': 25,
        'uselang': lang,
    }
    result = requests.get(url=url, params=params, headers={'User-agent': 'WikiMI QaM 1.0'})
    data = result.json()

    return data


def claim_qid(item_list, prop, with_ref=True):
    result = []
    for item in item_list:
        if "wikidatified" in item and item["wikidatified"]:
            result_item = {
                "mainsnak":
                    {"snaktype": "value",
                     "property": prop,
                     "datavalue":
                         {
                             "value":
                                 {
                                     "entity-type": "item",
                                     "numeric-id": int(item["qid"].strip("Q"))
                                 },
                             "type": "wikibase-entityid"
                         }
                     },
                "type": "statement",
                "rank": "normal"
            }
            if with_ref:
                result_item["references"] = references()
            result.append(result_item)
    return result


def claim_date(date, prop, with_ref=True):
    result = []

    if date.__len__() == 10:
        date = "+" + date + "T00:00:00Z"
        precision = 11
    elif date.__len__() == 7:
        date = "+" + date + "-00T00:00:00Z"
        precision = 10
    if date.__len__() == 4:
        date = "+" + date + "-00-00T00:00:00Z"
        precision = 9
    else:
        return []

    result_item = {
        "mainsnak":
            {"snaktype": "value",
             "property": prop,
             "datavalue":
                 {
                     "value":
                         {
                             "time": date,
                             "precision": precision,
                             "timezone": 0,
                             "before": 0,
                             "after": 0,
                             "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
                         },
                     "type": "time"
                 }
             },
        "type": "statement",
        "rank": "normal"
    }
    if with_ref:
        result_item["references"] = references()
    result.append(result_item)

    return result


def claim_monolingual(text, prop, lang="pt-br", with_ref=True):
    text_parts = textwrap.wrap(text, 1500, break_long_words=False, break_on_hyphens=False)
    result = []
    if text_parts:
        for order, part in enumerate(text_parts):
            result_item = {
                "mainsnak":
                    {
                        "snaktype": "value",
                        "property": prop,
                        "datavalue":
                            {
                                "value":
                                    {
                                        "text": part,
                                        "language": lang
                                    },
                                "type": "monolingualtext"
                            }
                    },
                "type": "statement",
                "rank": "normal",
            }
            if text_parts.__len__() > 1:
                result_item["qualifiers"] = order_qualifiers(order)

            if with_ref:
                result_item["references"] = references()
            result.append(result_item)
    return result


def claim_string(text, prop, with_ref=True):
    result = []

    result_item = {
        "mainsnak":
            {
                "snaktype": "value",
                "property": prop,
                "datavalue":
                    {
                        "value": text,
                        "type": "string"
                    }
            },
        "type": "statement",
        "rank": "normal"
    }
    if with_ref:
        result_item["references"] = references()
    result.append(result_item)
    return result


def labels(text, lang="pt-br"):
    return {lang: {"language": lang, "value": text}}


def descriptions(text, lang="pt-br"):
    return {lang: {"language": lang, "value": text}}


def references():
    today = datetime.today().strftime('+%Y-%m-%dT00:00:00Z')
    return [
        {
            "snaks":
                {
                    "P248":
                        [
                            {
                                "snaktype": "value",
                                "property": "P248",
                                "datavalue":
                                    {
                                        "value":
                                            {
                                                "entity-type": "item",
                                                "numeric-id": 10317762
                                            },
                                        "type": "wikibase-entityid"
                                    }
                            }
                        ],
                    "P813":
                        [
                            {
                                "snaktype": "value",
                                "property": "P813",
                                "datavalue":
                                    {
                                        "value":
                                            {
                                                "time": today,
                                                "precision": 11,
                                                "timezone": 0,
                                                "before": 0,
                                                "after": 0,
                                                "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
                                            },
                                        "type": "time"
                                    }
                            }
                        ]
                }
        }
    ]


def order_qualifiers(order):
    return {
        "P1545":
            [
                {
                    "snaktype": "value",
                    "property": "P1545",
                    "datavalue":
                        {
                            "value": order,
                            "type": "string"
                        }
                }
            ],
        "P1480":
            [
                {
                    "snaktype": "value",
                    "property": "P1480",
                    "datavalue":
                        {
                            "value":
                                {
                                    "entity-type": "item",
                                    "numeric-id": 105642994
                                },
                            "type": "wikibase-entityid"
                        }
                }
            ]
    }
