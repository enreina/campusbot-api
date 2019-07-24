from flask import Blueprint, request
import requests
import settings as env
import hashlib
from db.firestoreClient import db
import pywikibot
from google.cloud.firestore_v1.document import DocumentReference 
import json
from google.cloud import firestore

DEFAULT_GLOBE_ITEM = "http://www.wikidata.org/entity/Q2"

"""
    Notes:
    We need to remove the built in throttling because we 
    are working on our own localhost running wikibase, we don't
    care if we do a ton of requests, we are likely the only user
"""
# over write it
def wait(self, seconds):
    pass

pywikibot.throttle.Throttle.wait = wait

def globes():
    """Supported globes for Coordinate datatype."""
    return {
        'ariel': 'http://www.wikidata.org/entity/Q3343',
        'callisto': 'http://www.wikidata.org/entity/Q3134',
        'ceres': 'http://www.wikidata.org/entity/Q596',
        'deimos': 'http://www.wikidata.org/entity/Q7548',
        'dione': 'http://www.wikidata.org/entity/Q15040',
        'earth': 'http://www.wikidata.org/entity/Q2',
        'enceladus': 'http://www.wikidata.org/entity/Q3303',
        'eros': 'http://www.wikidata.org/entity/Q16711',
        'europa': 'http://www.wikidata.org/entity/Q3143',
        'ganymede': 'http://www.wikidata.org/entity/Q3169',
        'gaspra': 'http://www.wikidata.org/entity/Q158244',
        'hyperion': 'http://www.wikidata.org/entity/Q15037',
        'iapetus': 'http://www.wikidata.org/entity/Q17958',
        'io': 'http://www.wikidata.org/entity/Q3123',
        'jupiter': 'http://www.wikidata.org/entity/Q319',
        'lutetia': 'http://www.wikidata.org/entity/Q107556',
        'mars': 'http://www.wikidata.org/entity/Q111',
        'mercury': 'http://www.wikidata.org/entity/Q308',
        'mimas': 'http://www.wikidata.org/entity/Q15034',
        'miranda': 'http://www.wikidata.org/entity/Q3352',
        'moon': 'http://www.wikidata.org/entity/Q405',
        'oberon': 'http://www.wikidata.org/entity/Q3332',
        'phobos': 'http://www.wikidata.org/entity/Q7547',
        'phoebe': 'http://www.wikidata.org/entity/Q17975',
        'pluto': 'http://www.wikidata.org/entity/Q339',
        'rhea': 'http://www.wikidata.org/entity/Q15050',
        'steins': 'http://www.wikidata.org/entity/Q150249',
        'tethys': 'http://www.wikidata.org/entity/Q15047',
        'titan': 'http://www.wikidata.org/entity/Q2565',
        'titania': 'http://www.wikidata.org/entity/Q3322',
        'triton': 'http://www.wikidata.org/entity/Q3359',
        'umbriel': 'http://www.wikidata.org/entity/Q3338',
        'venus': 'http://www.wikidata.org/entity/Q313',
        'vesta': 'http://www.wikidata.org/entity/Q3030',
    }

wikibaseIntegrator = Blueprint('wikibaseIntegrator', __name__)
WIKIBASE_API_ENDPOINT = env.WIKIBASE_URL + "/w/api.php"
site = pywikibot.Site('en', 'campuswiki')
site.login()
repo = site.data_repository()
repo.globes = globes

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

@wikibaseIntegrator.route('/api/wikibase/create-item', methods=['GET', 'POST'])
def createItem(requestData=None):
    if request is not None and request.method == 'GET':
        return {'methodName': 'createItem'}
    else:
        if request.data:
            requestData = request.data
        description = requestData.get('description', None)
        label = requestData.get('label', None)
        wikibaseId = requestData.get('wikibaseId', None)
        itemData = requestData.get('item', {})

        # create item
        item = pywikibot.ItemPage(repo, title=wikibaseId)
        if not wikibaseId:
            item.editLabels(labels={"en": label}, summary=u"Set the new item's label")
            item.editDescriptions(descriptions={"en": description}, summary=u"Edit description")

        for propertyKey in itemData:
            if propertyKey not in ["label", "description"]:
                try:
                    # search property in database
                    results = db.collection("properties").where(u"aliases", u"array_contains", propertyKey).get()
                    for result in results:
                        propertyDict = result.to_dict()
                        propertyId = propertyDict.get('wikibaseId', None)
                        dataType = propertyDict.get('dataType', None)
                        if propertyId:
                            # add statement
                            claim = pywikibot.Claim(repo, propertyId)
                            target = itemData[propertyKey]
                            print(target)
                            # map according datatype
                            if dataType == 'string':
                                target = unicode(target)
                            elif dataType == 'globe-coordinate':
                                target = pywikibot.Coordinate(site=repo, lat=target['latitude'], lon=target['longitude'], precision=0.0001, globe_item=DEFAULT_GLOBE_ITEM)
                            elif dataType == 'quantity':
                                target = pywikibot.WbQuantity(target)
                            elif dataType == 'wikibase-item' and propertyKey == 'building' and isinstance(target, basestring):
                                target = findOrCreateBuilding(target)
                                print(target)

                            # map according to valueMap
                            if 'valueMap' in propertyDict:
                                print(propertyDict['valueMap'])
                                target = unicode(propertyDict['valueMap'][target])

                            if isinstance(target, DocumentReference):
                                target = target.get()
                                targetId = target.to_dict().get('wikibaseId', None)
                                target = pywikibot.ItemPage(repo, targetId)
                            
                            claim.setTarget(target)
                            # check duplicate claim
                            if claim not in item.get().get("claims", {}).get(propertyId,[]):
                                item.addClaim(claim, summary="Adding claim for " + propertyKey)
                                print("Adding claim for " + propertyKey)
                            break
                except Exception as e:
                    print "ERROR: ",propertyKey, e
                    continue

                
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
                    'item': categoryData
                }
                print(requestData)

                results = createItem(requestData)
                wikibaseId = results['itemID']

                # update property
                category.reference.update({'wikibaseId': wikibaseId})
                allResults.append(results)
            except:
                allResults.append({'success':0, 'categoryId':category.id})
                continue
        
        print(allResults)
        return allResults

@wikibaseIntegrator.route('/api/wikibase/place/create-item-from-db/<itemId>', methods=['GET', 'POST'])
def createItemFromDB(itemId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'createItem'}
    else:
        item = db.collection('placeItems').document(itemId).get()
        itemData = item.to_dict()
        requestData = {
            'label': itemData.get('name', itemId),
            'description': itemData.get('route', None),
            'wikibaseId': itemData.get('wikibaseId', None),
            'item': itemData
        }
        print(requestData)
        results = createItem(requestData)
        print(results)
        wikibaseId = results['itemID']

        item.reference.update({'wikibaseId': wikibaseId})

        return results

def findOrCreateBuilding(name):
    items = db.collection('placeItems').where(u'nameLower', u'==', name.lower()).get()
    for item in items:
        itemData = item.to_dict()
        if itemData.get('categoryName', '') == 'Building':
            # create wikibase instance
            createItemFromDB(item.id)
            return db.collection('placeItems').document(item.id)

    # create new building 
    newBuilding = db.collection('placeItems').document()
    newBuilding.set(
        {
            "name": name,
            "category": db.collection('categories').document('building'),
            "categoryName": 'Building',
            "createdAt": firestore.SERVER_TIMESTAMP
        }
    )
    createItemFromDB(newBuilding.id)
    return db.collection('placeItems').document(item.id)
    
