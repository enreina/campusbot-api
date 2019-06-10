from flask import Blueprint, request
from db.firestoreClient import db
from firebase_admin import firestore
from common.constants import taskType
from datetime import datetime, timedelta
from dateutil.tz import tzlocal 

trashBinTaskAssignment = Blueprint('trashBinTaskAssignment', __name__)

# Trash bin Task Generation & Assignment
# hit this endpoint every monday and wednesday for each item
@trashBinTaskAssignment.route('/api/trashbin/generate-enrichment-task', methods=['GET', 'POST'])
def generateTrashBinEnrichmentTaskAllItem():
    if request is not None and request.method == 'GET':
        return {'methodName': 'generateTrashBinEnrichmentTaskAllItem'}
    
    # clean all task instances
    users = db.collection('users').get()
    userIds = [user.id for user in users]
    for userId in userIds:
        userRef = db.collection('users').document(userId)
        taskInstancesQuery = userRef.collection('trashBinTaskInstances')
        taskInstancesQuery = taskInstancesQuery.where(u'completed', '==', False)
        taskInstancesQuery = taskInstancesQuery.where(u'expired', '==', False)
        taskInstances = taskInstancesQuery.get()
        for taskInstance in taskInstances:
            taskInstanceDict = taskInstance.to_dict()
            expirationDate = taskInstanceDict.get('expirationDate', None)
            if expirationDate is not None and expirationDate < datetime.now(tzlocal()):
                # set expired to true
                userRef.collection('trashBinTaskInstances').document(taskInstance.id).update({'expired': True})

    trashBinItems = db.collection('trashBinItems').get()
    counter = 0
    taskIds = []
    for item in trashBinItems:
        try:
            result = generateTrashBinEnrichmentTask(item.id)
            if 'taskId' in result:
                counter = counter + 1
                taskIds.append(result['taskId'])
        except:
            continue

    return {'taskIds': taskIds, 'message': "Task generated for {counter} items".format(counter=counter)}

# hit the endpoint by mobile app and chatbot after creation
@trashBinTaskAssignment.route('/api/trashbin/generate-enrichment-task/<itemId>', methods=['GET', 'POST'])
def generateTrashBinEnrichmentTask(itemId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'generateTrashBinEnrichmentTask'}
    else:
        # get the item
        item = db.collection('trashBinItems').document(itemId)
        itemDict = item.get().to_dict()
        # find task with the same itemId
        tasks = db.collection('trashBinTasks').where(u'itemId',u'==', itemId).where(u'type', u'==', taskType.TASK_TYPE_ENRICH_ITEM).order_by('createdAt', direction=firestore.Query.DESCENDING).get()
        tasks = [x for x in tasks]
        if tasks:
            answersCount = tasks[0].to_dict().get('answersCount',{}).copy()
        else:
            answersCount = {
                'wasteType': [],
                'size': [],
                'color': [],
            }
        
        for propertyKey in answersCount:
            if propertyKey in itemDict:
                answersCount[propertyKey].append({
                    'propertyValue': itemDict[propertyKey],
                    'propertyCount': 1
                })

        # set expiration time to 2 days from now
        expirationDate = datetime.now(tzlocal()) + timedelta(days=2)
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
        taskId = db.collection('trashBinTasks').add(taskData)
        # call assign trashbintask after task is generated
        assignTrashBinTask(taskId[1].id)

        del taskData['item']
        return {'taskId': taskId[1].id, 'task': taskData}

# hit the endpoint by mobile app and chatbot after enrichment task is completed
@trashBinTaskAssignment.route('/api/trashbin/generate-validation-task/<userId>/<enrichmentTaskInstanceId>', methods=['GET', 'POST'])
def generateTrashBinValidationTask(userId, enrichmentTaskInstanceId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'generateTrashBinValidationTask'}

    # get enrichment task instance
    taskInstanceRef = db.collection('users').document(userId).collection('trashBinTaskInstances').document(enrichmentTaskInstanceId)
    taskInstance = taskInstanceRef.get().to_dict()
    # get enrichment answers
    trashBinEnrichments = db.collection('trashBinEnrichments').where(u'taskInstance', u'==', taskInstanceRef).get()
    trashBinEnrichment = [x for x in trashBinEnrichments][0].to_dict()
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
            # convert waste type from number to nominal category
            if propertyKey == 'wasteType' and isinstance(propertyValue, int):
                if propertyValue == 0:
                    propertyValue = u"General Waste"
                elif propertyValue == 1:
                    propertyValue = u"Paper Cups"
                elif propertyValue == 2:
                    propertyValue = u"Others"

            if propertyKey in trashBinEnrichment and trashBinEnrichment[propertyKey] == propertyValue:
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
        if not added and propertyKey in trashBinEnrichment:
            newAnswersCount.append({
                'propertyValue': trashBinEnrichment[propertyKey], 
                'propertyCount': 1})
            counter = counter + 1
            if maxCount == 0:
                majorityAnswers[propertyKey] = trashBinEnrichment[propertyKey]

        answersCount[propertyKey] = newAnswersCount
        answersCountSufficient = answersCountSufficient and (counter >= taskDict['numOfAnswersRequired'])
    # update answers count in DB
    taskInstance['task'].update({'answersCount': answersCount})    
    
    # check if each answer count >= numOfRequiredAnswer
    if answersCountSufficient:
        # create aggregated answers dict
        aggregatedAnswers = {
            'imageUrl': itemDict['imageUrl'],
            'locationDescription': itemDict['locationDescription'],
            'building': itemDict['building']
        }
        if 'wasteType' in itemDict:
            aggregatedAnswers['wasteType'] = itemDict['wasteType']
        if 'size' in itemDict:
            aggregatedAnswers['size'] = itemDict['size']
        if 'color' in itemDict:
            aggregatedAnswers['color'] = itemDict['color']

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
        taskId = db.collection('trashBinTasks').add(taskData)
        # call assign trashbintask after task is generated
        assignTrashBinTask(taskId[1].id)

        del taskData['item']
        del taskData['aggregatedAnswers']
        return {'taskId': taskId[1].id, 'task': taskData}

    return {'message': 'Validation task was not generated'}

@trashBinTaskAssignment.route('/api/trashbin/assign-task/<taskId>')
def assignTrashBinTask(taskId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'assignTrashBinTask'}

    # get task and item
    taskRef = db.collection('trashBinTasks').document(taskId)
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
    
    allUsers = db.collection('users').order_by('totalTasksCompleted.trashbin', direction=firestore.Query.ASCENDING).get()
    allUsers = [x.id for x in allUsers]

    counter = 0
    if 'buildingName' in item and item['buildingName'] is not None:
        usersWithPreferredLocation = db.collection('users').where(u"preferredLocationNames", u"array_contains", item['buildingName'].lower()).order_by('totalTasksCompleted.trashbin', direction=firestore.Query.ASCENDING).get()
        usersWithPreferredLocation = [x.id for x in usersWithPreferredLocation]
    else:
        usersWithPreferredLocation = []

    # # generate task instance to each user with preferred location
    for userId in usersWithPreferredLocation:
        if userId != authorId:
            taskInstanceCollection = db.collection('users').document(userId).collection('trashBinTaskInstances')
            taskInstanceCollection.add(taskInstance)
            counter = counter + 1

    # # generate task if not enough task instance
    if counter < task['numOfAnswersRequired'] * 3:
        users = list(set(allUsers) - set(usersWithPreferredLocation))
        print(users)
        numOfUsersNeeded = task['numOfAnswersRequired'] * 3 - counter

        for userId in users[:numOfUsersNeeded]:
            if userId != authorId:
                taskInstanceCollection = db.collection('users').document(userId).collection('trashBinTaskInstances')
                taskInstanceCollection.add(taskInstance)
                counter = counter + 1

    
    return {'message': "Task instance generated for {counter} users".format(counter=counter)}

# hit this endpoint everytime a user registers
@trashBinTaskAssignment.route('/api/trashbin/assign-task-to-user/<userId>', methods=['GET', 'POST'])
def assignTrashBinTaskToUser(userId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'assignTrashBinTaskToUser'}
    # get tasks
    trashBinTasks = db.collection('trashBinTasks').order_by('createdAt', direction=firestore.Query.DESCENDING).limit(15).get()

    counter = 0
    for task in trashBinTasks:
        # prepare task instance
        taskDict = task.to_dict()
        if taskDict.get('doNotAssign', False):
            continue
        taskInstance = {
            'taskId': task.id,
            'task': db.collection('trashBinTasks').document(task.id),
            'createdAt': datetime.now(tzlocal()),
            'completed': False,
            'expired': False,
            'expirationDate': taskDict.get('expirationDate', None)
        }
        # assign task instance to user
        taskInstanceCollection = db.collection('users').document(userId).collection('trashBinTaskInstances')
        taskInstanceCollection.add(taskInstance)
        counter = counter + 1

    return {'message': '{counter} task instances assigned to user {userId}'.format(counter=counter, userId=userId)}

@trashBinTaskAssignment.route('/api/trashbin/generate-validation-task', methods=['GET', 'POST'])
def generateTrashBinValidationTaskAllEnrichmentTask():
    if request is not None and request.method == 'GET':
        return {'methodName': 'generateTrashBinValidationTaskAllEnrichmentTask'}

    # get all enrichment task ids which has not expired
    enrichmentTasks = db.collection('trashBinTasks').where('expirationDate', '>', datetime.now(tzlocal())).get()
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
        # create aggregated answers dict
        aggregatedAnswers = {
            'imageUrl': itemDict['imageUrl'],
            'locationDescription': itemDict['locationDescription']
        }
        if 'wasteType' in itemDict:
            aggregatedAnswers['wasteType'] = itemDict['wasteType']
        if 'size' in itemDict:
            aggregatedAnswers['size'] = itemDict['size']
        if 'color' in itemDict:
            aggregatedAnswers['color'] = itemDict['color']
        if 'building' in itemDict:
            aggregatedAnswers['building'] = itemDict['building']

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
        taskId = db.collection('trashBinTasks').add(taskData)
        # call assign trashbin after task is generated
        assignmentResult = assignTrashBinTask(taskId[1].id)
        assignmentResult['taskId'] = taskId[1].id
        validationTasks.append(taskData)
    
    return validationTasks