from flask import Blueprint, request
from db.firestoreClient import db
from firebase_admin import firestore
from common.constants import taskType
from datetime import datetime, timedelta
from dateutil.tz import tzlocal 

foodTaskAssignment = Blueprint('foodTaskAssignment', __name__)

# FOOD TASK GENERATION & ASSIGNMENT
# hit the endpoint by mobile app and chatbot after creation
@foodTaskAssignment.route('/api/food/generate-enrichment-task/<itemId>', methods=['GET', 'POST'])
def generateFoodEnrichmentTask(itemId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'generateFoodEnrichmentTask'}
    else:
        # get the item
        item = db.collection('foodItems').document(itemId)
        itemDict = item.get().to_dict()
        # generate the enrichment task
        answersCount = {
            'mealCategory': []
        }
    
        taskData = {
            'itemId': itemId,
            'item': item,
            'type': taskType.TASK_TYPE_ENRICH_ITEM,
            'numOfAnswersRequired': 5,
            'createdAt': datetime.now(tzlocal()),
            'expirationDate': None, # no expiration date
            'answersCount': answersCount
        }
        taskId = db.collection('foodTasks').add(taskData)
        # call assign foodtask after task is generated
        assignFoodTask(taskId[1].id)

        del taskData['item']
        return {'taskId': taskId[1].id, 'task': taskData}

# hit the endpoint by mobile app and chatbot after enrichment task is completed
@foodTaskAssignment.route('/api/food/generate-validation-task/<userId>/<enrichmentTaskInstanceId>', methods=['GET', 'POST'])
def generateFoodValidationTask(userId, enrichmentTaskInstanceId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'generateFoodValidationTask'}

    # get enrichment task instance
    taskInstanceRef = db.collection('users').document(userId).collection('foodTaskInstances').document(enrichmentTaskInstanceId)
    taskInstance = taskInstanceRef.get().to_dict()
    # get enrichment answers
    foodEnrichments = db.collection('foodEnrichments').where(u'taskInstance', u'==', taskInstanceRef).get()
    foodEnrichment = [x for x in foodEnrichments][0].to_dict()
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

    newCount = []
    for mealCategory in foodEnrichment['mealCategory']:
        newMealCategoryCount = []
        added = False
        counter = 0
        maxCount = 0
        for mealCategoryCountObject in answersCount['mealCategory']:
            isPropertyNameEqual = mealCategoryCountObject['propertyName'] == mealCategory['propertyName']
            isPropertyValueEqual = mealCategoryCountObject['propertyValue'] == mealCategory['propertyValue']
            
            if isPropertyNameEqual and isPropertyValueEqual:
                count = mealCategoryCountObject['propertyCount'] + 1
                added = True
                mealCategoryCountObject['propertyCount'] = count
                counter = counter + count
                if count > maxCount:
                    maxCount = count
                    majorityAnswers[mealCategory['propertyName']] = mealCategory['propertyValue']
            elif isPropertyNameEqual:
                count = mealCategoryCountObject['propertyCount'] 
                counter = counter + count 
                if count > maxCount:
                    maxCount = count
                    majorityAnswers[mealCategory['propertyName']] = mealCategoryCountObject['propertyValue']
        
        if not added:
            answersCount['mealCategory'].append(
                {'propertyName': mealCategory['propertyName'], 
                'propertyValue': mealCategory['propertyValue'], 
                'propertyCount': 1})
            counter = counter + 1
            if maxCount == 0:
                majorityAnswers[mealCategory['propertyName']] = mealCategory['propertyValue']
        answersCountSufficient = answersCountSufficient and (counter >= taskDict['numOfAnswersRequired'])
        
    # update answers count in DB
    taskInstance['task'].update({'answersCount': answersCount})    
    print(majorityAnswers)
    # check if each answer count >= numOfRequiredAnswer
    if answersCountSufficient:
        # create aggregated answers dict
        aggregatedAnswers = {
            'imageUrl': itemDict['imageUrl'],
            'name': itemDict['name'],
            'mealItems': itemDict['mealItems']
        }

        # generate task.aggregatedAnswers according to majority count
        aggregatedAnswers['categories'] = []
        for mealItem in majorityAnswers:
            aggregatedAnswers['categories'].append({
                'propertyName': mealItem,
                'propertyValue': majorityAnswers[mealItem]
            })
        
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
        taskId = db.collection('foodTasks').add(taskData)
        # call assign foodTask after task is generated
        assignFoodTask(taskId[1].id)

        del taskData['item']
        del taskData['aggregatedAnswers']
        return {'taskId': taskId[1].id, 'task': taskData}

    return {'message': 'Validation task was not generated'}

@foodTaskAssignment.route('/api/food/assign-task/<taskId>', methods=['GET', 'POST'])
def assignFoodTask(taskId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'assignFoodTask'}

    # get task and item
    taskRef = db.collection('foodTasks').document(taskId)
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
    
    users = db.collection('users').order_by('totalTasksCompleted.food', direction=firestore.Query.ASCENDING).get()
    users = [x.id for x in users]
    numOfUsersNeeded = task['numOfAnswersRequired'] * 3

    counter = 0
    for userId in users[:numOfUsersNeeded]:
        if userId != authorId:
            taskInstanceCollection = db.collection('users').document(userId).collection('foodTaskInstances')
            taskInstanceCollection.add(taskInstance)
            counter = counter + 1

    return {'message': "Task instance generated for {counter} users".format(counter=counter)}
