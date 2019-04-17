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
        tasks = db.collection('placeTasks').where('itemId', '==', itemId).where('type', '==', taskType.TASK_TYPE_ENRICH_ITEM).get()
        for task in tasks:
            return {'taskId': task.id}
        # get the item
        item = db.collection('placeItems').document(itemId)
        # generate the enrichment task
        answersCount = {
            'building': [],
            'buildingNumber': [],
            'floorNumber': [],
            'seatCapacity': []
        }
        taskData = {
            'itemId': item.id,
            'item': item,
            'type': taskType.TASK_TYPE_ENRICH_ITEM,
            'numOfAnswersRequired': 5,
            'currentNumOfAnswers': 0,
            'createdAt': datetime.now(tzlocal()),
            'expirationDate': None, # decide expiration date
            'answersCount': answersCount
        }
        taskId = db.collection('placeTasks').add(taskData)
        # call assign placetask after task is generated
        # assignPlaceEnrichmentTask(taskId)

        del taskData['item']
        return {'taskId': taskId[1].id, 'task': taskData}

@placeTaskAssignment.route('/api/place/assign-enrichment-task/<taskId>', methods=['GET', 'POST'])
def assignPlaceEnrichmentTask(taskId):

    if request is not None and request.method == 'GET':
        return {'methodName': 'assignPlaceEnrichmentTask'}
    # load all users except the author WITH preferredlocation
    # order by totalTasksCompleted (ascending)
    # if num of users < numOfRequiredAnswers * 2
    # load more users except the author WITHOUT prefferedlocation
    # limit num of users to numOfRequiredAnswers * 2

    # get task and item
    taskRef = db.collection('placeTasks').document(taskId)
    task = taskRef.get()
    item = task.to_dict()['item'].get()
    # get item's author
    authorId = item.to_dict()['authorId']
    taskInstance = {
        'taskId': taskId,
        'task': taskRef,
        'createdAt': datetime.now(tzlocal()),
        'completed': False
    }

    users = db.collection('users').order_by('totalTasksCompleted.place', direction=firestore.Query.ASCENDING).get()
    counter = 0
    # generate task instance to each user
    for user in users:
        print(user)
        if user.id != authorId:
            taskInstanceCollection = db.collection('users').document(user.id).collection('placeTaskInstances')
            taskInstanceCollection.add(taskInstance)
            counter = counter + 1
    
    return {'message': "Task instance generated for {counter} users".format(counter=counter)}

# hit the endpoint by mobile app and chatbot after enrichment task is completed
@placeTaskAssignment.route('/api/place/generate-validate-task/:enrichmentTaskId')
def generatePlaceValidationTask(enrichmentTaskId):
    # check if aggregatedAnswers >= numOfRequiredAnswer

    # count the majority of answer (include answers from created item)
    # generate task.data according to majority count

    # call assign place validation task
    return {'methodName': 'generatePlaceValidationTask'}

@placeTaskAssignment.route('/api/place/assign-validation-task/<itemId>')
def assignPlaceValidationTask(itemId):
    # load all users except the author WITH preferredlocation
    # order by totalTasksCompleted (ascending)
    # if num of users < numOfRequiredAnswers
    # load more users except the author WITHOUT preferredlocation
    # limit num of users to numOfRequiredAnswers

    # generate task instance to each user
    return {'methodName': 'assignPlaceValidationTask'}