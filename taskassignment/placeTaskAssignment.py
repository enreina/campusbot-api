from flask import Blueprint, request
from db.firestoreClient import db
from firebase_admin import firestore
from common.constants import taskType
from datetime import datetime, timedelta
from dateutil.tz import tzlocal

placeTaskAssignment = Blueprint('placeTaskAssignment', __name__)

# Place Task Generation & Assignment
# hit this endpoint every day for each place task instance
@placeTaskAssignment.route('/api/place/generate-enrichment-task', methods=['GET', 'POST'])
def generatePlaceEnrichmentTaskAllItem():
    if request is not None and request.method == 'GET':
        return {'methodName': 'generatePlaceEnrichmentTaskAllItem'}
    
    # clean all task instances
    users = db.collection('users').get()
    userIds = [user.id for user in users]
    for userId in userIds:
        userRef = db.collection('users').document(userId)
        taskInstancesQuery = userRef.collection('placeTaskInstances')
        taskInstancesQuery = taskInstancesQuery.where(u'completed', '==', False)
        taskInstancesQuery = taskInstancesQuery.where(u'expired', '==', False)
        taskInstances = taskInstancesQuery.get()
        for taskInstance in taskInstances:
            taskInstanceDict = taskInstance.to_dict()
            expirationDate = taskInstanceDict.get('expirationDate', None)
            if expirationDate is not None and expirationDate < datetime.now(tzlocal()):
                # set expired to true
                userRef.collection('placeTaskInstances').document(taskInstance.id).update({'expired': True})

    placeItems = db.collection('placeItems').get()
    counter = 0
    taskIds = []
    for item in placeItems:
        try:
            result = generatePlaceEnrichmentTask(item.id)
            if 'taskId' in result:
                counter = counter + 1
                taskIds.append(result['taskId'])
        except:
            continue

    return {'taskIds': taskIds, 'message': "Task generated for {counter} items".format(counter=counter)}

# hit the endpoint by mobile app and chatbot after creation
@placeTaskAssignment.route('/api/place/generate-enrichment-task/<itemId>',  methods=['GET', 'POST'])
def generatePlaceEnrichmentTask(itemId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'generatePlaceEnrichmentTask'}
    else:
        # get the item
        item = db.collection('placeItems').document(itemId)
        itemDict = item.get().to_dict()

        # find task with the same itemId
        tasks = db.collection('placeTasks').where(u'itemId',u'==', itemId).where(u'type', u'==', taskType.TASK_TYPE_ENRICH_ITEM).order_by('createdAt', direction=firestore.Query.DESCENDING).get()
        tasks = [x for x in tasks]
        if tasks:
            answersCount = tasks[0].to_dict().get('answersCount',{}).copy()
        elif itemDict['category'] == db.collection('categories').document('building'):
            answersCount = {
                'buildingNumber': [],
                'seatCapacity': []
            }
            if 'buildingNumber' in itemDict:
                answersCount['buildingNumber'].append({
                    'propertyValue': itemDict['buildingNumber'],
                    'propertyCount': 1
                })
            if 'seatCapacity' in itemDict:
                answersCount['seatCapacity'].append({
                    'propertyValue': itemDict['seatCapacity'],
                    'propertyCount': 1
                })
        else:
            answersCount = {
                'buildingName': [],
                'floorNumber': [],
                'seatCapacity': []
            }
            if 'buildingName' in itemDict:
                answersCount['buildingName'].append({
                    'propertyValue': itemDict['buildingName'],
                    'propertyCount': 1
                })
            if 'floorNumber' in itemDict:
                answersCount['floorNumber'].append({
                    'propertyValue': itemDict['floorNumber'],
                    'propertyCount': 1
                })
            if 'seatCapacity' in itemDict:
                answersCount['seatCapacity'].append({
                    'propertyValue': itemDict['seatCapacity'],
                    'propertyCount': 1
                })

        expirationDate = datetime.now(tzlocal()) + timedelta(days=1)
        expirationDate = expirationDate.replace(hour=0, minute=0, second=0, microsecond=0)

        taskData = {
            'itemId': itemId,
            'item': item,
            'type': taskType.TASK_TYPE_ENRICH_ITEM,
            'numOfAnswersRequired': 5,
            'createdAt': datetime.now(tzlocal()),
            'expirationDate': expirationDate, # expiration date to one day
            'answersCount': answersCount
        }
        taskId = db.collection('placeTasks').add(taskData)
        # call assign placetask after task is generated
        assignPlaceTask(taskId[1].id)

        del taskData['item']
        del taskData['answersCount']
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
                majorityAnswers[propertyKey] = placeEnrichment[propertyKey]

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
        elif 'route' in placeEnrichment:
            aggregatedAnswers['route'] = placeEnrichment['route']

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
        'completed': False,
        'expired': False,
        'expirationDate': task['expirationDate']
    }
    
    allUsers = db.collection('users').order_by('totalTasksCompleted.place', direction=firestore.Query.ASCENDING).get()
    allUsers = [x.id for x in allUsers]

    counter = 0
    if 'buildingName' in item and item['buildingName'] is not None:
        usersWithPreferredLocation = db.collection('users').where(u"preferredLocationNames", u"array_contains", item['buildingName'].lower()).order_by('totalTasksCompleted.place', direction=firestore.Query.ASCENDING).get()
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

# hit this endpoint everytime a user registers
@placeTaskAssignment.route('/api/place/assign-task-to-user/<userId>', methods=['GET', 'POST'])
def assignPlaceTaskToUser(userId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'assignPlaceTaskToUser'}
    # get tasks
    placeTasks = db.collection('placeTasks').order_by('createdAt', direction=firestore.Query.DESCENDING).limit(15).get()

    counter = 0
    for task in placeTasks:
        # prepare task instance
        taskDict = task.to_dict()
        if taskDict.get('doNotAssign', False):
            continue
        taskInstance = {
            'taskId': task.id,
            'task': db.collection('placeTasks').document(task.id),
            'createdAt': datetime.now(tzlocal()),
            'completed': False,
            'expired': False,
            'expirationDate': taskDict.get('expirationDate', None)
        }
        # assign task instance to user
        taskInstanceCollection = db.collection('users').document(userId).collection('placeTaskInstances')
        taskInstanceCollection.add(taskInstance)
        counter = counter + 1

    return {'message': '{counter} task instances assigned to user {userId}'.format(counter=counter, userId=userId)}

@placeTaskAssignment.route('/api/place/generate-validation-task', methods=['GET', 'POST'])
def generatePlaceValidationTaskAllEnrichmentTask():
    if request is not None and request.method == 'GET':
        return {'methodName': 'generatePlaceValidationTaskAllEnrichmentTask'}

    # get all enrichment task ids which has not expired
    enrichmentTasks = db.collection('placeTasks').where('expirationDate', '>', datetime.now(tzlocal())).get()
    validationTasks = []
    # for every enrichment task
    for task in enrichmentTasks:
        taskDict = task.to_dict()
        # skip if not enrichment task
        if taskDict['type'] != taskType.TASK_TYPE_ENRICH_ITEM:
            continue
        # calculate majority
        answersCount = taskDict['answersCount']
        majorityAnswers = {}
        for propertyKey in answersCount:
            maxCount = 0
            for propertyCountObject in answersCount[propertyKey]:
                if propertyCountObject['propertyCount'] > maxCount:
                    maxCount = propertyCountObject['propertyCount']
                    majorityAnswers[propertyKey] = propertyCountObject['propertyValue']
        # get item
        itemRef = taskDict['item']
        item = itemRef.get()
        itemDict = item.to_dict()
        # create aggregatedAnswers
        aggregatedAnswers = {
            'imageUrl': itemDict['imageUrl'],
            'name': itemDict['name'],
            'geolocation': itemDict['geolocation'],
            'category': itemDict['category'],
            'categoryName': itemDict['categoryName']
        }
        if 'route' in itemDict:
            aggregatedAnswers['route'] = itemDict['route']

        if 'hasElectricityOutlet' in itemDict:
            aggregatedAnswers['hasElectricityOutlet'] = itemDict['hasElectricityOutlet']

        # generate task.aggregatedAnswers according to majority count
        for propertyKey in majorityAnswers:
            aggregatedAnswers[propertyKey] = majorityAnswers[propertyKey]
        
        # create validation task
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
        validationTasks.append(taskData)
        try:
            assignmentResult = assignPlaceTask(taskId[1].id)
            assignmentResult['taskId'] = taskId[1].id
        except:
            continue
    
    return validationTasks

