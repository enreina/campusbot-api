from flask import Blueprint

placeTaskAssignment = Blueprint('placeTaskAssignment', __name__)

# Place Task Generation & Assignment
# hit this endpoint every day for each item
@placeTaskAssignment.route('/api/place/generate-enrichment-task')
def generatePlaceEnrichmentTaskAllItem():
    # call generatePlaceEnrichmentTask
    return {'methodName': 'generatePlaceEnrichmentTaskAllItem'}

# hit the endpoint by mobile app and chatbot after creation
@placeTaskAssignment.route('/api/place/generate-enrichment-task/<itemId>')
def generatePlaceEnrichmentTask(itemId):
    # call assign placetask after task is generated
    return {'methodName': 'generatePlaceEnrichmentTask'}

@placeTaskAssignment.route('/api/place/assign-enrichment-task/<itemId>')
def assignPlaceEnrichmentTask(itemId):
    # load all users except the author WITH preferredlocation
    # order by totalTasksCompleted (ascending)
    # if num of users < numOfRequiredAnswers * 2
    # load more users except the author WITHOUT prefferedlocation
    # limit num of users to numOfRequiredAnswers * 2

    # generate task instance to each user
    return {'methodName': 'assignPlaceEnrichmentTask'}

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