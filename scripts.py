from lxml import etree
import re
import requests
import collections
import time

#
# # Namespaces
# ns = {
#     'srw_dc': 'info:srw/schema/1/dc-schema',
#     'dc': 'http://purl.org/dc/elements/1.1/',
#     'srw': 'http://www.loc.gov/zing/srw/',
#     'xsi': 'http://www.w3.org/2001/XMLSchema'
# }
#
# attributes = ('tipoDocumento',
#               'date',
#               'urn',
#               'localidade',
#               'autoridade',
#               'title',
#               'description',
#               'identifier',
#               'subject')
#
#
# # The script uses two classes to store the information scrapped from the LeXML api
# class Law:
#     """This class stores data about legislation entities"""
#
#     def __init__(self, tipoDocumento='', date='', urn='', localidade='', autoridade='', title='', description='',
#                  identifier='', subject=None):
#         """Initial class to store the data about legislation entities
#
#         Attributes
#         ----------
#         tipoDocumento: str
#             type of legislation
#         date: str
#             date of promulgation
#         urn: str
#             identifier of the legislation item in the database
#         localidade: str
#             locality where the legislation has authority
#         autoridade: str
#             entity that issued the legislation
#         title: str
#             official name of the legislation
#         description: str
#             legislation long title, or digest, summarizing the content of the legislation
#         identifier: str
#             unique identifier in the database
#         subject: list
#             keywords of the legislation
#         """
#
#         self.tipoDocumento = tipoDocumento
#         self.date = date
#         self.urn = urn
#         self.localidade = localidade
#         self.autoridade = autoridade
#         self.title = title
#         self.description = description
#         self.identifier = identifier
#         self.subject = subject or []
#
#     def print_self(self):
#         """
#          Function that returns the data separated by a '*' character
#         """
#         return (self.tipoDocumento + '*' +
#                 self.date + '*' +
#                 self.urn + '*' +
#                 self.localidade + '*' +
#                 self.autoridade + '*' +
#                 self.title + '*' +
#                 self.description + '*' +
#                 self.identifier + '*' +
#                 '*'.join(self.subject) +
#                 '\n')
#
#
# class Lexicon:
#     """Used for keeping track of how many times each legislation subject (keyword) was used"""
#
#     def __init__(self, word='', count=0):
#         """Initial class to store data about the lexicon
#
#         Attributes
#         ----------
#         word: str
#             term of the lexicon
#         count: int
#             number of occurences of the term
#         """
#
#         self.word = word
#         self.count = count


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

    for attr in item.iter():
        tag = attr.tag

        # Some tags present a prefix namespace, so we strip them to get the proper name of the tag
        if '}' in tag:
            tag = tag.split('}')[1]

        # We only want the information of the defined tags, everything else is ignored
        if tag in attributes:
            if tag != 'subject':
                if attr.text:
                    attr.text = attr.text.replace('\n', '')
                setattr(new_law, tag, attr.text)
            else:
                subjects = [keyword.strip() for keyword in re.split(r'\s[,.]\s', attr.text)]
                unique_subjects = list(set(subjects))

                # Strip unnecessary ' .' in the end of the subjects, usually present in the last keywords
                for i in range(0, len(unique_subjects)):
                    if ' .' in unique_subjects[i]:
                        unique_subjects[i] = unique_subjects[i][:-2]
                setattr(new_law, tag, unique_subjects)
    return new_law


def print_scraped_info(laws, filename):
    """Print the information scrapped from the API into a file

    Parameters
    ----------
    laws : list
        list of law items ready to be printed into a file
    filename : str
        name of the file to be printed the scraped laws information
    """

    file = open(filename + '.txt', 'w+')
    file.write('tipo de documento*data*urn*localidade*autoridade*título*descricao*identifier*assuntos->\n')
    for law_item in laws:
        file.write(law_item.print_self())
    file.close()


def get_lexicon(laws):
    lex = []
    for law_item in laws:
        for keyword in law_item.subject:
            lex.append(keyword)
    lexicon = collections.Counter(lex)
    lexicon = sorted(lexicon.items(), key=lambda _lex: lex[1], reverse=True)
    return lexicon


def print_lexicon(lexicon, filename):
    file_lex = open(filename + '_lexicon.txt', 'w')
    for key, value in lexicon:
        file_lex.write(str(value) + '*' + key + '\n')
    file_lex.close()


search_term = '"federal+decreto.lei"'
base_url = 'https://www.lexml.gov.br/busca/SRU?operation=searchRetrieve&query=urn+=' + \
           search_term + '&maximumRecords=500&startRecord='
file_name = 'saida'
n = 2
lexicon_flag = True


@app.route('/')
def hello_world():
    laws = []
    for i in range(0, n):
        url = base_url + str(i * 500 + 1)
        req = requests.get(url)
        req.encoding = 'utf-8'
        tree = etree.fromstring(req.content)

        # x stands for each entry in <srw_dc:dc>
        for x in tree.findall('.//srw_dc:dc', namespaces=ns):
            new_law = get_values(x)
            laws.append(new_law)

        # Being polite
        time.sleep(2)

    if lexicon_flag:
        lexicon = get_lexicon(laws)
        print_lexicon(lexicon, file_name)

    print_scraped_info(laws, file_name)
    return 'Hello World!'


if __name__ == '__main__':
    app.run()
