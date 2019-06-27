from flask import Blueprint, request
import requests
import settings as env
import hashlib
from db.firestoreClient import db
import pywikibot
import json

wikibaseIntegrator = Blueprint('wikibaseIntegrator', __name__)
API_ENDPOINT = env.WIKIBASE_URL + "/w/api.php"
site = pywikibot.Site('en', 'campuswiki')
site.login()

@wikibaseIntegrator.route('/api/wikibase/create-all-accounts', methods=['GET', 'POST'])
def createAllAccounts():
    if request is not None and request.method == 'GET':
        return {'methodName': 'createAllAccounts'}
    else:
        # get all chatbot users
        getUsers = db.collection('users').get()
        allUsers = [x for x in getUsers]
        results = []
        count = 0
        # create account for all chatbot users
        for user in allUsers:
            userData = user.to_dict()
            if userData.get('telegramId', False):
                try:
                    res = createWikibaseAccount(userData['telegramId'])
                    results.append(res)
                    if res['createaccount']['status'] == 'PASS':
                        count = count + 1
                except:
                    continue

        return {
            "message": "{countSuccess} out of {countTotal} accounts succesfully created".format(countSuccess=count, countTotal=len(results)),
            "results": results
        }


@wikibaseIntegrator.route('/api/wikibase/create-account/<username>', methods=['GET', 'POST'])
def createWikibaseAccount(username):
    if request is not None and request.method == 'GET':
        return {'methodName': 'createWikibaseAccount'}
    else:
        # Retrieve account creation token from `tokens` module
        session = requests.Session()

        params = {
            'action': "query",
            'meta': "tokens",
            'type': "createaccount",
            'format': "json"
        }
        response = session.get(url=API_ENDPOINT, params=params)
        responseData = response.json()

        token = responseData['query']['tokens']['createaccounttoken']
        print(env.WIKIBASE_PASSWORD_SALT)
        password = hashlib.md5("{salt}{username}".format(salt=env.WIKIBASE_PASSWORD_SALT, username=username)).hexdigest()
        # send account information
        params = {
            'action': 'createaccount',
            'createtoken': token,
            'username': username,
            'password': password,
            'retype': password,
            'createreturnurl': env.WIKIBASE_URL,
            'format': 'json'
        }
        print(params)

        response = session.post(url=API_ENDPOINT, data=params)
        return response.json()

@wikibaseIntegrator.route('/api/wikibase/create-property', methods=['GET', 'POST'])
def createProperty():
    if request is not None and request.method == 'GET':
        return {'methodName': 'createWikibaseAccount'}
    else:
        datatype = request.data.get('datatype', None)
        description = request.data.get('description', None)
        label = request.data.get('label', None)

        data = {
            'datatype': datatype,
            'descriptions': {
                'en': {
                    'language': 'en',
                    'value': description
                }
            },
            'labels': {
                'en': {
                    'language': 'en',
                    'value': label
                }
            }
        }

        params = {
            'action': 'wbeditentity',
            'new': 'property',
            'data': json.dumps(data),
            'summary': 'bot adding in properties',
            'token': site.tokens['edit']
        }

        req = site._simple_request(**params)
        results = req.submit()
        
        return results




