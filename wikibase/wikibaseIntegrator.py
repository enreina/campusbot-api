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
            item.editLabels(labels={"en": label}, summary=u"Set the item's label")
        if description is not None:
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
                            # map according to valueMap
                            if 'valueMap' in propertyDict:
                                target = propertyDict['valueMap'][unicode(target)]

                            # map according datatype
                            if dataType == 'string':
                                target = unicode(target)
                            elif dataType == 'globe-coordinate':
                                target = pywikibot.Coordinate(site=repo, lat=target['latitude'], lon=target['longitude'], precision=0.0001, globe_item=DEFAULT_GLOBE_ITEM)
                            elif dataType == 'quantity':
                                target = pywikibot.WbQuantity(target)
                            elif dataType == 'wikibase-item' and propertyKey == 'building' and isinstance(target, basestring):
                                target = findOrCreateBuilding(target)
                            elif dataType == 'wikibase-item' and propertyKey == 'mealItems':
                                target = findOrCreateMealItems(target)

                            if not isinstance(target, list):
                                target = [target]

                            for targetItem in target:
                                if isinstance(targetItem, DocumentReference):
                                    targetItem = targetItem.get()
                                    targetId = targetItem.to_dict().get('wikibaseId', None)
                                    targetItem = pywikibot.ItemPage(repo, targetId)

                                claim.setTarget(targetItem)
                                if 'qualifiers' in propertyDict:
                                    for qualifierData in propertyDict['qualifiers']:
                                        qualifier = pywikibot.Claim(repo, qualifierData['propertyId'])
                                        targetQualifier = itemData[qualifierData['propertyValueKey']]
                                        if qualifierData['dataType'] == 'string':
                                            targetQualifier = unicode(targetQualifier)
                                        qualifier.setTarget(targetQualifier)
                                        claim.addQualifier(qualifier)
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

                results = createItem(requestData)
                wikibaseId = results['itemID']

                # update property
                category.reference.update({'wikibaseId': wikibaseId})
                allResults.append(results)
            except:
                allResults.append({'success':0, 'categoryId':category.id})
                continue
        
        return allResults

@wikibaseIntegrator.route('/api/wikibase/place/create-item-from-db/<itemId>', methods=['GET', 'POST'])
def createPlaceItemFromDB(itemId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'createPlaceItem'}
    else:
        item = db.collection('placeItems').document(itemId).get()
        itemData = item.to_dict()
        requestData = {
            'label': itemData.get('name', itemId),
            'description': itemData.get('route', None),
            'wikibaseId': itemData.get('wikibaseId', None),
            'item': itemData
        }
        results = createItem(requestData)
        wikibaseId = results['itemID']

        item.reference.update({'wikibaseId': wikibaseId})

        return results

@wikibaseIntegrator.route('/api/wikibase/place/create-all-items', methods=['GET', 'POST'])
def createAllPlaceItems():
    if request is not None and request.method == 'GET':
        return {'methodName': 'createAllPlaceItems'}
    else:
        allResults = []
        placeItems = db.collection("placeItems").get()
        for item in placeItems:
            print("Creating Place Item: {placeName}".format(
                placeName=item.to_dict().get("name"))
            )

            results = createPlaceItemFromDB(item.id)
            allResults.append(results)
        return allResults

def findOrCreateBuilding(name):
    items = db.collection('placeItems').where(u'nameLower', u'==', name.lower()).get()
    for item in items:
        itemData = item.to_dict()
        if itemData.get('categoryName', '') == 'Building':
            # create wikibase instance
            createPlaceItemFromDB(item.id)
            return db.collection('placeItems').document(item.id)

    # create new building 
    newBuilding = db.collection('placeItems').document()
    newBuilding.set(
        {
            "name": name,
            "nameLower": name.lower(),
            "category": db.collection('categories').document('building'),
            "categoryName": u'Building',
            "createdAt": firestore.SERVER_TIMESTAMP
        }
    )
    createPlaceItemFromDB(newBuilding.id)
    return db.collection('placeItems').document(item.id)

@wikibaseIntegrator.route('/api/wikibase/trashbin/create-item-from-db/<itemId>', methods=['GET', 'POST'])
def createTrashBinItemFromDB(itemId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'createTrashBinItemFromDB'}
    else:
        item = db.collection('trashBinItems').document(itemId).get()
        itemData = item.to_dict()
        itemData[u'category'] = db.collection('categories').document('trash-bin')
        requestData = {
            'label': unicode("Trash Bin #{itemId}".format(itemId=item.id)),
            'description': unicode(itemData.get('locationDescription', None)),
            'wikibaseId': itemData.get('wikibaseId', None),
            'item': itemData
        }
        results = createItem(requestData)
        wikibaseId = results['itemID']

        item.reference.update({'wikibaseId': wikibaseId})

        return results

@wikibaseIntegrator.route('/api/wikibase/trashbin/create-all-items', methods=['GET', 'POST'])
def createAllTrashBinItems():
    if request is not None and request.method == 'GET':
        return {'methodName': 'createAllTrashBinItems'}
    else:
        allResults = []
        trashBinItems = db.collection("trashBinItems").get()
        for item in trashBinItems:
            try:
                print("Creating Trash Bin Item: {trashBinName}".format(
                    trashBinName=item.to_dict().get("locationDescription"))
                )

                results = createTrashBinItemFromDB(item.id)
                allResults.append(results)
            except Exception as e:
                print "ERROR: ", e
                continue

        return allResults

@wikibaseIntegrator.route('/api/wikibase/food/create-item-from-db/<itemId>', methods=['GET', 'POST'])
def createFoodItemFromDB(itemId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'createFoodItemFromDB'}
    else:
        item = db.collection('foodItems').document(itemId).get()
        itemData = item.to_dict()
        if 'category' not in itemData:
            itemData[u'category'] = db.collection('categories').document('meal')
            description = u"A meal containing {}".format(unicode(itemData.get('name', None)))
        else:
            description = unicode(itemData.get('name', None))

        requestData = {
            'label': unicode(itemData.get('name', None)),
            'description': description,
            'wikibaseId': itemData.get('wikibaseId', None),
            'item': itemData
        }
        results = createItem(requestData)
        wikibaseId = results['itemID']

        item.reference.update({'wikibaseId': wikibaseId})

        return results

@wikibaseIntegrator.route('/api/wikibase/food/create-all-items', methods=['GET', 'POST'])
def createAllFoodItems():
    if request is not None and request.method == 'GET':
        return {'methodName': 'createAllFoodItems'}
    else:
        allResults = []
        foodItems = db.collection("foodItems").get()
        for item in foodItems:
            try:
                print("Creating Food Item: {foodName}".format(
                    foodName=item.to_dict().get("name"))
                )

                results = createFoodItemFromDB(item.id)
                allResults.append(results)
            except Exception as e:
                print "ERROR: ", e
                continue

        return allResults

def findOrCreateMealItems(target):
    mealItemList = []
    for mealItem in target:
        # find in meal items collection
        queriedItems = db.collection('foodItems').where('name', '==', mealItem.lower()).get()
        found = False
        for item in queriedItems:
            itemDict = item.to_dict()
            if itemDict.get('category', None) == db.collection('categories').document('food'):
                mealItemList.append(db.collection('foodItems').document(item.id))
                found = True
                break
        
        # if not found, create new item
        if not found:
            newItem = db.collection('foodItems').document()
            newItem.set(
                {
                    "name": mealItem.lower(),
                    "category": db.collection('categories').document('food'),
                    "createdAt": firestore.SERVER_TIMESTAMP
                }
            )
            createFoodItemFromDB(newItem.id)
            mealItemList.append(db.collection("foodItems").document(newItem.id))

    return mealItemList

@wikibaseIntegrator.route('/api/wikibase/place/import-enrichments', methods=['GET', 'POST'])
def importPlaceEnrichments():
    if request is not None and request.method == 'GET':
        return {'methodName': 'importPlaceEnrichments'}
    else:
        results = []
        enrichments = db.collection('placeEnrichments').get()
        for enrichment in enrichments:
            try:
                enrichmentData = enrichment.to_dict()
                print(enrichmentData)
                # find item
                item = enrichmentData['taskInstance'].get().get('task').get().get('item').get()
                itemData = item.to_dict()
                wikibaseId = itemData.get('wikibaseId', False)

                requestData = {
                    "item": enrichmentData,
                    "wikibaseId": wikibaseId
                }
                print(requestData)

                results.append(createItem(requestData))
            except Exception as e:
                print(e)
                continue
        return results

