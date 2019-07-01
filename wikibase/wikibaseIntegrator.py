from flask import Blueprint, request
import requests
import settings as env
import hashlib
from db.firestoreClient import db
import pywikibot
from google.cloud.firestore_v1.document import DocumentReference 

wikibaseIntegrator = Blueprint('wikibaseIntegrator', __name__)
WIKIBASE_API_ENDPOINT = env.WIKIBASE_URL + "/w/api.php"
site = pywikibot.Site('en', 'campuswiki')
site.login()
repo = site.data_repository()

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

        response = session.post(url=WIKIBASE_API_ENDPOINT, data=params)
        return response.json()

@wikibaseIntegrator.route('/api/wikibase/create-property', methods=['GET', 'POST'])
def createProperty(requestData=None):
    if request is not None and request.method == 'GET':
        return {'methodName': 'createProperty'}
    else:
        if request.data:
            requestData = request.data
        datatype = requestData.get('datatype', None)
        description = requestData.get('description', None)
        label = requestData.get('label', None)

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
        # 
        return results

@wikibaseIntegrator.route('/api/wikibase/create-all-properties', methods=['GET', 'POST'])
def createAllProperties():
    if request is not None and request.method == 'GET':
        return {'methodName': 'createAllProperties'}
    else:
        # get all properties from database
        allProperties = db.collection('properties').get()
        allResults = []
        # loop; don't create property for properties which already has wikibaseId
        for propertyItem in allProperties:
            propertyData = propertyItem.to_dict()
            if propertyData.get('wikibaseId', False):
                continue
            try:
                # call create property
                requestData = {
                    'datatype': propertyData.get('dataType', None),
                    'description': propertyData.get('description', None),
                    'label': propertyData.get('label', None)
                }

                results = createProperty(requestData)
                wikibaseId = results['entity']['id']

                # update property
                propertyItem.reference.update({'wikibaseId': wikibaseId})
                allResults.append(results)
            except:
                allResults.append({'success':0, 'property':propertyData})

        return allResults

@wikibaseIntegrator.route('/api/wikibase/create-category', methods=['GET', 'POST'])
def createCategory(requestData=None):
    if request is not None and request.method == 'GET':
        return {'methodName': 'createCategory'}
    else:
        if request.data:
            requestData = request.data
        description = requestData.get('description', None)
        label = requestData.get('label', None)
        wikibaseId = requestData.get('wikibaseId', None)
        categoryData = requestData.get('category', {})

        # create item
        item = pywikibot.ItemPage(repo, title=wikibaseId)
        if not wikibaseId:
            item.editLabels(labels={"en": label}, summary=u"Set the new item's label")
            item.editDescriptions(descriptions={"en": description}, summary=u"Edit description")
        
        for propertyKey in categoryData:
            if propertyKey not in ["label", "description"]:
                # search property in database
                results = db.collection("properties").where(u"aliases", u"array_contains", propertyKey).get()
                for result in results:
                    propertyId = result.to_dict().get('wikibaseId', None)
                    if propertyId:
                        # add statement
                        claim = pywikibot.Claim(repo, propertyId)
                        target = categoryData[propertyKey]
                        print(target)
                        print(isinstance(target, DocumentReference))
                        if isinstance(target, DocumentReference):
                            target = target.get()
                            targetId = target.to_dict().get('wikibaseId', None)
                            print(targetId)
                            target = pywikibot.ItemPage(repo, targetId)
                            claim.setTarget(target)
                            item.addClaim(claim, summary="Adding claim for " + propertyKey)
                            break

                
        # return result
        return {"itemID": item.getID(), "label": label, "description": description}

@wikibaseIntegrator.route('/api/wikibase/create-all-categories', methods=['GET', 'POST'])
def createAllCategories():
    if request is not None and request.method == 'GET':
        return {'methodName': 'createAllCategories'}
    else:
        # get all categories from database
        allCategories = db.collection('categories').get()
        allResults = []
        # loop; don't create property for properties which already has wikibaseId
        for category in allCategories:
            categoryData = category.to_dict()
            try:
                # call create property
                requestData = {
                    'description': categoryData.get('description', None),
                    'label': categoryData.get('label', None),
                    'wikibaseId': categoryData.get('wikibaseId', None),
                    'category': categoryData
                }

                results = createCategory(requestData)
                wikibaseId = results['itemID']

                # update property
                category.reference.update({'wikibaseId': wikibaseId})
                allResults.append(results)
            except:
                allResults.append({'success':0, 'category':requestData})

        return allResults