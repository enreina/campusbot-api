from flask import Blueprint, request
from db.firestoreClient import db
from firebase_admin import firestore
from common.constants import taskType
from datetime import datetime, timedelta
from dateutil.tz import tzlocal 

questionTaskAssignment = Blueprint('questionTaskAssignment', __name__)

# Course Task Generation & Assignment
# hit the endpoint by mobile app and chatbot after creation
@questionTaskAssignment.route('/api/question/generate-enrichment-task/<itemId>', methods=["GET", "POST"])
def generateQuestionEnrichmentTask(itemId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'generateQuestionEnrichmentTask'}
    else:
        # get the item
        item = db.collection('questionItems').document(itemId)
        itemDict = item.get().to_dict()
        # generate the enrichment task
        answersCount = {
            'answer': []
        }

        # set expiration time to 5 days from now
        expirationDate = datetime.now(tzlocal()) + timedelta(days=5)
        expirationDate = expirationDate.replace(hour=0, minute=0, second=0, microsecond=0)
    
        taskData = {
            'itemId': itemId,
            'item': item,
            'type': taskType.TASK_TYPE_ENRICH_ITEM,
            'numOfAnswersRequired': 3,
            'createdAt': datetime.now(tzlocal()),
            'expirationDate': expirationDate,
            'answersCount': answersCount
        }
        taskId = db.collection('questionTasks').add(taskData)
        # call assign questiontask after task is generated
        assignQuestionTask(taskId[1].id)

        del taskData['item']
        return {'taskId': taskId[1].id, 'task': taskData}

# hit the endpoint by mobile app and chatbot after enrichment task is completed
@questionTaskAssignment.route('/api/question/generate-validation-task/<userId>/<enrichmentTaskInstanceId>', methods=['GET', 'POST'])
def generateQuestionValidationTask(userId, enrichmentTaskInstanceId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'generateQuestionValidationTask'}

    # get enrichment task instance
    taskInstanceRef = db.collection('users').document(userId).collection('questionTaskInstances').document(enrichmentTaskInstanceId)
    taskInstance = taskInstanceRef.get().to_dict()
    # get enrichment answers
    questionEnrichments = db.collection('questionEnrichments').where(u'taskInstance', u'==', taskInstanceRef).get()
    questionEnrichment = [x for x in questionEnrichments][0].to_dict()
    # get task
    task = taskInstance['task'].get()
    taskId = task.id
    taskDict = task.to_dict()
    # get task item
    itemRef = taskDict['item']
    item = itemRef.get()
    itemDict = item.to_dict()
    # update answers
    answersCount = taskDict['answersCount']
    answers = answersCount['answer']
    answers.append({
        'propertyValue': questionEnrichment['answer'],
        'propertyCount': 1
    })
    answersCount['answer'] = answers
    taskInstance['task'].update({'answersCount': answersCount})
    # all task instances are completed 
    # OR expiration time is done
    if len(answers) >= taskDict['numOfAnswersRequired'] * 3 or taskDict['expirationDate'] < datetime.now(tzlocal()):
        # generate task.aggregatedAnswer containing all current answers
        aggregatedAnswers = {
            'courseName': itemDict['courseName'],
            'question': itemDict['question'],
            'answers': [x['propertyValue'] for x in answers]
        }
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
        taskId = db.collection('questionTasks').add(taskData)
        # call assign questiontask after task is generated
        assignQuestionTask(taskId[1].id)

        del taskData['item']
        del taskData['aggregatedAnswers']
        return {'taskId': taskId[1].id, 'task': taskData}

    return {'message': 'Validation task was not generated'}

@questionTaskAssignment.route('/api/question/assign-task/<taskId>', methods=['GET', 'POST'])
def assignQuestionTask(taskId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'assignQuestionTask'}

    # get task and item
    taskRef = db.collection('questionTasks').document(taskId)
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
    
    allUsers = db.collection('users').order_by('totalTasksCompleted.question', direction=firestore.Query.ASCENDING).get()
    allUsers = [x.id for x in allUsers]

    counter = 0
    if 'courseCode' in item and item['courseCode'] is not None:
        usersWithPreferredCourse = db.collection('users').where(u"preferredCourses", u"array_contains", item['courseCode'].lower()).order_by('totalTasksCompleted.question', direction=firestore.Query.ASCENDING).get()
        usersWithPreferredCourse = [x.id for x in usersWithPreferredCourse]
    else:
        usersWithPreferredCourse = []

    # # generate task instance to each user with preferred location
    for userId in usersWithPreferredCourse:
        if userId != authorId:
            taskInstanceCollection = db.collection('users').document(userId).collection('questionTaskInstances')
            taskInstanceCollection.add(taskInstance)
            counter = counter + 1

    # # generate task if not enough task instance
    if counter < task['numOfAnswersRequired'] * 3:
        users = list(set(allUsers) - set(usersWithPreferredCourse))
        numOfUsersNeeded = task['numOfAnswersRequired'] * 3 - counter

        for userId in users[:numOfUsersNeeded]:
            if userId != authorId:
                taskInstanceCollection = db.collection('users').document(userId).collection('questionTaskInstances')
                taskInstanceCollection.add(taskInstance)
                counter = counter + 1

    
    return {'message': "Task instance generated for {counter} users".format(counter=counter)}

# hit this endpoint everytime a user registers
@questionTaskAssignment.route('/api/question/assign-task-to-user/<userId>', methods=['GET', 'POST'])
def assignQuestionTaskToUser(userId):
    if request is not None and request.method == 'GET':
        return {'methodName': 'assignQuestionTaskToUser'}
    # get tasks
    questionTasks = db.collection('questionTasks').order_by('createdAt', direction=firestore.Query.DESCENDING).limit(15).get()

    counter = 0
    for task in questionTasks:
        # prepare task instance
        taskDict = task.to_dict()
        if taskDict.get('doNotAssign', False):
            continue
        taskInstance = {
            'taskId': task.id,
            'task': db.collection('questionTasks').document(task.id),
            'createdAt': datetime.now(tzlocal()),
            'completed': False,
            'expired': False,
            'expirationDate': taskDict.get('expirationDate', None)
        }
        # assign task instance to user
        taskInstanceCollection = db.collection('users').document(userId).collection('questionTaskInstances')
        taskInstanceCollection.add(taskInstance)
        counter = counter + 1

    return {'message': '{counter} task instances assigned to user {userId}'.format(counter=counter, userId=userId)}