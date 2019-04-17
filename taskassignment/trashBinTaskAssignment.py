from flask import Blueprint

trashBinTaskAssignment = Blueprint('trashBinTaskAssignment', __name__)

# Trash bin Task Generation & Assignment
# hit this endpoint every monday and wednesday for each item
@trashBinTaskAssignment.route('/api/trashbin/generate-enrichment-task')
def generateTrashBinEnrichmentTaskAllItem():
    # call generatetrashbinEnrichmentTask
    return {'methodName': 'generateTrashBinEnrichmentTaskAllItem'} #replace this

# hit the endpoint by mobile app and chatbot after creation
@trashBinTaskAssignment.route('/api/trashbin/generate-enrichment-task/<itemId>')
def generateTrashBinEnrichmentTask(itemId):
    # call assign trashbintask after task is generated
    return {'methodName': 'generateTrashBinEnrichmentTask'} #replace this

@trashBinTaskAssignment.route('/api/trashbin/assign-enrichment-task/<itemId>')
def assignTrashBinEnrichmentTask(itemId):
    # load all users except the author WITH preferredlocation
    # order by totalTasksCompleted (ascending)
    # if num of users < numOfRequiredAnswers * 2
    # load more users except the author WITHOUT prefferedlocation
    # limit num of users to numOfRequiredAnswers * 2

    # generate task instance to each user
    return {'methodName': 'assignTrashBinEnrichmentTask'} #replace this

# hit the endpoint by mobile app and chatbot after enrichment task is completed
@trashBinTaskAssignment.route('/api/trashbin/generate-validate-task/:enrichmentTaskId')
def generateTrashBinValidationTask(enrichmentTaskId):
    # check if aggregatedAnswers >= numOfRequiredAnswer

    # count the majority of answer (include answers from created item)
    # generate task.data according to majority count

    # call assign trashbin validation task
    return {'methodName': 'generateTrashBinEnrichmentTask'} #replace this

@trashBinTaskAssignment.route('/api/trashbin/assign-validation-task/<itemId>')
def assignTrashBinValidationTask(itemId):
    # load all users except the author WITH preferredlocation
    # order by totalTasksCompleted (ascending)
    # if num of users < numOfRequiredAnswers
    # load more users except the author WITHOUT preferredlocation
    # limit num of users to numOfRequiredAnswers

    # generate task instance to each user
    return {'methodName': 'assignTrashBinValidationTask'} #replace this

