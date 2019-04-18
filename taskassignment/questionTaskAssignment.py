from flask import Blueprint

questionTaskAssignment = Blueprint('questionTaskAssignment', __name__)

# Course Task Generation & Assignment
# hit the endpoint by mobile app and chatbot after creation
@questionTaskAssignment.route('/api/question/generate-enrichment-task/<itemId>')
def generateQuestionEnrichmentTask(itemId):
    #
    # call assign questiontask after task is generated
    return {'methodName': 'generateQuestionEnrichmentTask'} #replace this

@questionTaskAssignment.route('/api/question/assign-enrichment-task/<itemId>')
def assignQuestionEnrichmentTask(itemId):
    # load all users except the author WITH preferred courses
    # order by totalTasksCompleted (ascending)
    # if num of users < numOfRequiredAnswers
    # load more users except the author WITHOUT prefrredcourse
    # limit num of users to numOfRequiredAnswers

    # generate task instance to each user
    return {'methodName': 'assignQuestionEnrichmentTask'} #replace this

# hit the endpoint by mobile app and chatbot after enrichment task is completed
@questionTaskAssignment.route('/api/question/generate-validation-task/<enrichmentTaskId>')
def generateQuestionValidationTask(enrichmentTaskId):
    # all task instances are completed 
    # OR expiration time is done

    # generate task.data containing all current answers

    # call assign Question validation task
    return {'methodName': 'generateQuestionValidationTask'} #replace this

@questionTaskAssignment.route('/api/question/assign-validation-task/<itemId>')
def assignQuestionValidationTask(itemId):
    # load all users except the author WITH preferred courses
    # order by totalTasksCompleted (ascending)
    # if num of users < numOfRequiredAnswers
    # load more users except the author WITHOUT prefrredcourse
    # limit num of users to numOfRequiredAnswers

    # generate task instance to each user
    return {'methodName': 'assignQuestionValidationTask'} #replace this