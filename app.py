import os
import yaml
import re
import json
from flask import Flask, render_template, request, redirect, session, jsonify, g
from flask_babel import Babel, gettext
from api import call_api, check_lexml_id_in_wikidata, post_search_entity, Law
from oauth_wikidata import get_username, get_token
from requests_oauthlib import OAuth1Session

__dir__ = os.path.dirname(__file__)
app = Flask(__name__)
app.config.update(yaml.safe_load(open(os.path.join(__dir__, 'config.yaml'))))

BABEL = Babel(app)


@app.before_request
def init_profile():
    g.profiling = []


@app.before_request
def global_user():
    g.user = get_username()


@app.route('/login')
def login():
    next_page = request.args.get('next')
    if next_page:
        session['after_login'] = next_page

    client_key = app.config['CONSUMER_KEY']
    client_secret = app.config['CONSUMER_SECRET']
    base_url = 'https://www.wikidata.org/w/index.php'
    request_token_url = base_url + '?title=Special%3aOAuth%2finitiate'

    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          callback_uri='oob')
    fetch_response = oauth.fetch_request_token(request_token_url)

    session['owner_key'] = fetch_response.get('oauth_token')
    session['owner_secret'] = fetch_response.get('oauth_token_secret')

    base_authorization_url = 'https://www.wikidata.org/wiki/Special:OAuth/authorize'
    authorization_url = oauth.authorization_url(base_authorization_url,
                                                oauth_consumer_key=client_key)
    return redirect(authorization_url)


@app.route("/oauth-callback", methods=["GET"])
def oauth_callback():
    base_url = 'https://www.wikidata.org/w/index.php'
    client_key = app.config['CONSUMER_KEY']
    client_secret = app.config['CONSUMER_SECRET']

    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          resource_owner_key=session['owner_key'],
                          resource_owner_secret=session['owner_secret'])

    oauth_response = oauth.parse_authorization_response(request.url)
    verifier = oauth_response.get('oauth_verifier')
    access_token_url = base_url + '?title=Special%3aOAuth%2ftoken'
    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          resource_owner_key=session['owner_key'],
                          resource_owner_secret=session['owner_secret'],
                          verifier=verifier)

    oauth_tokens = oauth.fetch_access_token(access_token_url)
    session['owner_key'] = oauth_tokens.get('oauth_token')
    session['owner_secret'] = oauth_tokens.get('oauth_token_secret')
    next_page = session.get('after_login')

    return redirect(next_page)


@BABEL.localeselector
def get_locale():
    """
    Function to get the current language of the session

    Returns
    ----------
    str
        String object containing the language of the session, defined by the browser of the user.
        Default: en
    """
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    return session.get('lang', 'en')


@app.route('/set_locale')
def set_locale():
    """
    Function to set a different language for the content. It returns the same page, with the new language
    """
    next_page = request.args.get('return_to')
    lang = request.args.get('lang')

    session["lang"] = lang
    return redirect(next_page)


@app.route('/')
@app.route('/inicio')
@app.route('/home')
def home():
    """
    Function to show the homepage of the application
    """
    lang = get_locale()
    username = get_username()
    return render_template('home.html', lang=lang, username=username)


@app.route('/reconciliate')
def reconciliate():
    lang = get_locale()
    username = get_username()
    return render_template('reconciliate.html', lang=lang, username=username)


@app.route('/reconciliate/<cat>')
def reconciliate_category(cat):
    lang = get_locale()
    username = get_username()
    if cat == 'authority' or cat == 'locality' or cat == 'type' or cat == 'subject':
        with open(os.path.join(app.static_folder, 'unknown.json'), encoding="utf-8") as file:
            unknown_values = json.load(file)[cat]

    return render_template(cat+'.html', unknown_values=unknown_values, lang=lang, username=username)


@app.route('/add_entry', methods=['POST', 'GET'])
def create_item_based_in_url():
    url = request.form['url'] if 'url' in request.form else ''
    return redirect('/add_entry/'+url)


@app.route('/add_entry/<path:url>', methods=['POST', 'GET'])
def create_item_based_in_url_with_url(url=None):
    if url is None:
        url = request.form['url'] if 'url' in request.form else ''
    lexml_id, valid_url = check_lexml_url(url)
    lang = get_locale()
    username = get_username()

    if valid_url:
        law, lexicon, message, status_api = call_api(
            lexml_id.replace(":", "+").replace(";", "+").replace("-", "+").replace(",", "+"))
        already_exists, item = check_if_already_exists(lexml_id)
        item_law = law.wikidatify_self()
        if not already_exists and status_api:
            qs = law.qs_self()
        else:
            qs = remove_stat_self(item_law, item).qs_self()
        return render_template('create.html',
                               lang=lang,
                               item_law=item_law,
                               qs=qs,
                               qid=item.qid,
                               tipoDocumento=item_law["tipoDocumento"],
                               date=item_law["date"],
                               urn=item_law["urn"],
                               localidade=item_law["localidade"],
                               autoridade=item_law["autoridade"],
                               title=item_law["title"],
                               description=item_law["description"],
                               subject=item_law["subject"],
                               username=username)
    else:
        return home()


def remove_stat_self(item_law, item_wd):
    if not item_wd.date:
        item_wd.date = item_law["date"]
    else:
        item_wd.date = ''
    if not item_wd.urn:
        item_wd.urn = item_law["urn"]
    else:
        item_wd.urn = ''
    if not item_wd.title:
        item_wd.title = item_law["title"]
    else:
        item_wd.title = ''
    if not item_wd.description:
        item_wd.description = item_law["description"]
    else:
        item_wd.description = ''
    if not item_wd.facet_tipoDocumento:
        item_wd.facet_tipoDocumento = [item_law["tipoDocumento"][0]["label"]]
    else:
        item_wd.facet_autoridade = []
    if not item_wd.country:
        item_wd.country = item_law["country"]
    else:
        item_wd.country = []
    if not item_wd.lang:
        item_wd.lang = item_law["lang"]
    else:
        item_wd.lang = []
    if not item_wd.wikiproject:
        item_wd.wikiproject = item_law["wikiproject"]
    else:
        item_wd.wikiproject = []
    if not item_wd.facet_localidade:
        item_wd.facet_localidade = item_law["localidade"][0]["label"]
    else:
        item_wd.facet_localidade = []
    if not item_wd.facet_autoridade:
        item_wd.facet_autoridade = item_law["autoridade"][0]["label"]
    else:
        item_wd.facet_localidade = []

    item_wd.subject = [x["label"] for x in item_law["subject"]]
    return item_wd


# Requisição para procurar entidades e filtrá-las pelos tesauros
@app.route('/search', methods=['GET', 'POST'])
def search_entity():
    if request.method == "POST":
        data = request.get_json()
        term = data['term']
        lang = get_locale()

        data = post_search_entity(term, lang)

        items = []
        if "search" in data:
            for item in data["search"]:
                if "id" in item and "label" in item and "description" in item:
                    items.append({"qid": item["id"],
                                  "label": item["label"],
                                  "descr": item["description"]})
        return jsonify(items), 200


def check_lexml_url(url):
    match = re.match(r"https://www.lexml.gov.br/urn/(.*)", url)
    if match:
        return match.groups()[0], True
    elif url == "":
        return gettext(u"Please provide a URL"), False
    else:
        return gettext(u"Invalid URL"), False


def check_if_already_exists(lexml_id):
    query_result = check_lexml_id_in_wikidata(lexml_id)

    item_law = Law(qid='')
    if len(query_result) > 0:
        if "subject" in query_result[0]:
            query_result[0]["subject"]["value"] = query_result[0]["subject"]["value"].split(";")

        for key in query_result[0].keys():
            setattr(item_law, key, query_result[0][key]["value"])

        return True, item_law
    else:
        return False, item_law


@app.route('/add_stat', methods=['GET', 'POST'])
def add_statement():
    if request.method == 'POST':
        data = request.get_json()
        qid = data['qid']
        term = data['term']
        filename = data['category'].lower() + ".json"

        if data["qid"] != "unknown":
            with open(os.path.join(app.static_folder, filename), encoding="utf-8") as file:
                lexicon = json.load(file)
            if term and qid:
                lexicon[term] = qid
            with open(os.path.join(app.static_folder, filename), 'w', encoding="utf-8") as file:
                json.dump(lexicon, file, ensure_ascii=False)

            with open(os.path.join(app.static_folder, "unknown.json"), encoding="utf-8") as file:
                lexicon_unk = json.load(file)
                lexicon_unk[data['category'].lower()].remove(term)
            with open(os.path.join(app.static_folder, "unknown.json"), 'w', encoding="utf-8") as file:
                json.dump(lexicon_unk, file, ensure_ascii=False)
        else:
            with open(os.path.join(app.static_folder, "unknown.json"), encoding="utf-8") as file:
                lexicon = json.load(file)
                lexicon[data['category'].lower()].append(term)
            with open(os.path.join(app.static_folder, "unknown.json"), 'w', encoding="utf-8") as file:
                json.dump(lexicon, file, ensure_ascii=False)

        return jsonify("200")
    else:
        return jsonify("204")


if __name__ == '__main__':
    app.run()
