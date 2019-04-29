from flask import Blueprint
from db.firestoreClient import db
from firebase_admin import firestore
from common.constants import taskType
from datetime import datetime
from dateutil.tz import tzlocal
from flask import request
from google.cloud.firestore_v1beta1.document import DocumentReference 

placeTaskAssignment = Blueprint('placeTaskAssignment', __name__)

# Place Task Generation & Assignment
# hit this endpoint every day for each item
@placeTaskAssignment.route('/api/place/generate-enrichment-task')
def generatePlaceEnrichmentTaskAllItem():
    # call generatePlaceEnrichmentTask
    return {'methodName': 'generatePlaceEnrichmentTaskAllItem'}

# hit the endpoint by mobile app and chatbot after creation
@placeTaskAssignment.route('/api/place/generate-enrichment-task/<itemId>',  methods=['GET', 'POST'])
def generatePlaceEnrichmentTask(itemId):
    if request.method == 'GET':
        return {'methodName': 'generatePlaceEnrichmentTask'}
    else:
        # check for task duplicate
        # tasks = db.collection('placeTasks').where('itemId', '==', itemId).where('type', '==', taskType.TASK_TYPE_ENRICH_ITEM).get()
        # for task in tasks:
        #     return {'taskId': task.id}
        # get the item
        item = db.collection('placeItems').document(itemId)
        itemDict = item.get().to_dict()
        # generate the enrichment task
        if item['category'] == db.collection('categories').document('building'):
            answersCount = {
                'buildingNumber': [],
                'seatCapacity': []
            }
            if 'buildingNumber' in item:
                answersCount['buildingNumber'].append({
                    'propertyValue': item['buildingNumber'],
                    'propertyCount': 1
                })
            if 'seatCapacity' in item:
                answersCount['seatCapacity'].append({
                    'propertyValue': item['seatCapacity'],
                    'propertyCount': 1
                })
        else:
            answersCount = {
                'building': [],
                'floorNumber': [],
                'seatCapacity': []
            }
            answersCount['building'].append({
                'propertyValue': item['building'],
                'propertyCount': 1
            })
            if 'floorNumber' in item:
                answersCount['floorNumber'].append({
                    'propertyValue': item['floorNumber'],
                    'propertyCount': 1
                })
            if 'seatCapacity' in item:
                answersCount['seatCapacity'].append({
                    'propertyValue': item['seatCapacity'],
                    'propertyCount': 1
                })

        
        taskData = {
            'itemId': item.id,
            'item': item,
            'type': taskType.TASK_TYPE_ENRICH_ITEM,
            'numOfAnswersRequired': 5,
            'createdAt': datetime.now(tzlocal()),
            'expirationDate': None, # decide expiration date
            'answersCount': answersCount
        }
        taskId = db.collection('placeTasks').add(taskData)
        # call assign placetask after task is generated
        assignPlaceTask(taskId[1].id)

        del taskData['item']
        return {'taskId': taskId[1].id, 'task': taskData}
# hit the endpoint by mobile app and chatbot after enrichment task is completed
@placeTaskAssignment.route('/api/place/generate-validation-task/<userId>/<enrichmentTaskInstanceId>', methods=['GET', 'POST'])
def generatePlaceValidationTask(userId, enrichmentTaskInstanceId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'generatePlaceValidationTask'}

    # get enrichment task instance
    taskInstanceRef = db.collection('users').document(userId).collection('placeTaskInstances').document(enrichmentTaskInstanceId)
    taskInstance = taskInstanceRef.get().to_dict()
    # get enrichment answers
    placeEnrichments = db.collection('placeEnrichments').where(u'taskInstance', u'==', taskInstanceRef).get()
    placeEnrichment = [x for x in placeEnrichments][0].to_dict()
    # get task
    task = taskInstance['task'].get()
    taskId = task.id
    taskDict = task.to_dict()
    # get task item
    itemRef = taskDict['item']
    item = itemRef.get()
    itemDict = item.to_dict()
    # update answers count
    answersCount = taskDict['answersCount']
    answersCountSufficient = True
    majorityAnswers = {}
    for propertyKey in answersCount: 
        newAnswersCount = []
        counter = 0
        added = False
        maxCount = 0
        for propertyCountObject in answersCount[propertyKey]:
            propertyValue = propertyCountObject['propertyValue']
            propertyCount = propertyCountObject['propertyCount']
            if propertyKey in placeEnrichment and placeEnrichment[propertyKey] == propertyValue:
                newAnswersCount.append({
                    'propertyValue': propertyValue, 
                    'propertyCount': propertyCount+1})
                counter = counter + propertyCount + 1
                added = True
            else:
                newAnswersCount.append({
                    'propertyValue': propertyValue, 
                    'propertyCount': propertyCount})
                counter = counter + propertyCount
            if newAnswersCount[-1]['propertyCount'] > maxCount:
                maxCount = newAnswersCount[-1]['propertyCount']
                majorityAnswers[propertyKey] = propertyValue
        if not added and propertyKey in placeEnrichment:
            newAnswersCount.append({
                'propertyValue': placeEnrichment[propertyKey], 
                'propertyCount': 1})
            counter = counter + 1
            if maxCount == 0:
                majorityAnswers[propertyKey] = propertyValue

        answersCount[propertyKey] = newAnswersCount
        answersCountSufficient = answersCountSufficient and (counter >= taskDict['numOfAnswersRequired'])
    # update answers count in DB
    taskInstance['task'].update({'answersCount': answersCount})    
    
    # check if each answer count >= numOfRequiredAnswer
    if answersCountSufficient:
        # create aggregated answers dict
        aggregatedAnswers = {
            'imageUrl': itemDict['imageUrl'],
            'name': itemDict['name'],
            'geolocation': itemDict['geolocation'],
            'category': itemDict['category'],
            'categoryName': itemDict['categoryName']
        }
        if 'route' in itemDict:
            aggregatedAnswers['route'] = itemDict['route']
        elif 'route' in taskEnrichment:
            aggregatedAnswers['route'] = itemDict['route']

        if 'hasElectricityOutlet' in itemDict:
            aggregatedAnswers['hasElectricityOutlet'] = itemDict['hasElectricityOutlet']

        # generate task.aggregatedAnswers according to majority count
        for propertyKey in majorityAnswers:
            aggregatedAnswers[propertyKey] = majorityAnswers[propertyKey]
        
        # generate task
        taskData = {
            'itemId': item.id,
            'item': itemRef,
            'type': taskType.TASK_TYPE_VALIDATE_ITEM,
            'numOfAnswersRequired': 5,
            'createdAt': datetime.now(tzlocal()),
            'expirationDate': None, # decide expiration date
            'aggregatedAnswers': aggregatedAnswers
        }
        taskId = db.collection('placeTasks').add(taskData)
        # call assign placetask after task is generated
        assignPlaceTask(taskId[1].id)

        del taskData['item']
        del taskData['aggregatedAnswers']
        return {'taskId': taskId[1].id, 'task': taskData}

    # call assign place validation task
    return {'message': 'Validation task was not generated'}

@placeTaskAssignment.route('/api/place/assign-task/<taskId>', methods=['GET', 'POST'])
def assignPlaceTask(taskId):

    if request is not None and request.method == 'GET':
        return {'methodName': 'assignPlaceTask'}

    # get task and item
    taskRef = db.collection('placeTasks').document(taskId)
    task = taskRef.get().to_dict()
    item = task['item'].get().to_dict()
    # get item's author
    authorId = item['authorId']
    taskInstance = {
        'taskId': taskId,
        'task': taskRef,
        'createdAt': datetime.now(tzlocal()),
        'completed': False
    }
    
    allUsers = db.collection('users').order_by('totalTasksCompleted.place', direction=firestore.Query.ASCENDING).get()
    allUsers = [x.id for x in allUsers]

    counter = 0
    if item['buildingNameLower'] is not None:
        usersWithPreferredLocation = db.collection('users').where(u"preferredLocationNames", u"array_contains", item['buildingNameLower']).order_by('totalTasksCompleted.place', direction=firestore.Query.ASCENDING).get()
        usersWithPreferredLocation = [x.id for x in usersWithPreferredLocation]
    else:
        usersWithPreferredLocation = []

    # # generate task instance to each user with preferred location
    for userId in usersWithPreferredLocation:
        if userId != authorId:
            taskInstanceCollection = db.collection('users').document(userId).collection('placeTaskInstances')
            taskInstanceCollection.add(taskInstance)
            counter = counter + 1

    # # generate task if not enough task instance
    if counter < task['numOfAnswersRequired'] * 3:
        users = list(set(allUsers) - set(usersWithPreferredLocation))
        print(users)
        numOfUsersNeeded = task['numOfAnswersRequired'] * 3 - counter

        for userId in users[:numOfUsersNeeded]:
            if userId != authorId:
                taskInstanceCollection = db.collection('users').document(userId).collection('placeTaskInstances')
                taskInstanceCollection.add(taskInstance)
                counter = counter + 1

    
    return {'message': "Task instance generated for {counter} users".format(counter=counter)}
