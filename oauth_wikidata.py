from flask import current_app, session
from requests_oauthlib import OAuth1Session
from urllib.parse import urlencode


def raw_request(params):
    app = current_app
    url = 'https://www.wikidata.org/w/api.php?' + urlencode(params)
    client_key = app.config['CONSUMER_KEY']
    client_secret = app.config['CONSUMER_SECRET']
    oauth = OAuth1Session(client_key,
                          client_secret=client_secret,
                          resource_owner_key=session['owner_key'],
                          resource_owner_secret=session['owner_secret'])
    return oauth.get(url, timeout=4)


def api_request(params):
    return raw_request(params).json()


def userinfo_call():
    params = {'action': 'query', 'meta': 'userinfo', 'format': 'json'}
    return api_request(params)


def get_username():
    if 'owner_key' not in session:
        return  # not authorized

    if 'username' in session:
        return session['username']

    reply = userinfo_call()
    if 'query' not in reply:
        return
    session['username'] = reply['query']['userinfo']['name']

    return session['username']


def get_token():
    params = {
        'action': 'query',
        'meta': 'tokens',
        'format': 'json',
        'formatversion': 2,
    }
    reply = api_request(params)
    token = reply['query']['tokens']['csrftoken']
    return token