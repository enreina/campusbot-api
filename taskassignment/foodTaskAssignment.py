from flask import Blueprint

foodTaskAssignment = Blueprint('foodTaskAssignment', __name__)

# FOOD TASK GENERATION & ASSIGNMENT
# hit the endpoint by mobile app and chatbot after creation
@foodTaskAssignment.route('/api/food/generate-enrichment-task/<itemId>')
def generateFoodEnrichmentTask(itemId):
    # 
    # call assign foodtask after task is generated
    return {'methodName': 'generateFoodEnrichmentTask', 'itemId': itemId} #replace this

@foodTaskAssignment.route('/api/food/assign-enrichment-task/<itemId>')
def assignFoodEnrichmentTask(itemId):
    # load all users except the author
    # order by totalTasksCompleted (ascending)
    # limit num of users to numOfRequiredAnswers * 2

    # generate task instance to each user
    return {'methodName': 'assignFoodEnrichmentTask', 'itemId': itemId} #replace this

# hit the endpoint by mobile app and chatbot after enrichment task is completed
@foodTaskAssignment.route('/api/food/generate-validate-task/<enrichmentTaskId>')
def generateFoodValidationTask(enrichmentTaskId):
    # check if aggregatedAnswers >= numOfRequiredAnswer
    # AND all task instances are completed

    # count the majority of answer (include answers from created item)
    # generate task.data according to majority count

    # call assign food validation task
    return {'methodName': 'generateFoodValidationTask', 'enrichmentTaskId': enrichmentTaskId} #replace this

@foodTaskAssignment.route('/api/food/assign-validation-task/<itemId>')
def assignFoodValidationTask(itemId):
    # load all users except the author
    # order by totalTasksCompleted (ascending)
    # limit num of users to numOfRequiredAnswers

    # generate task instance to each user
    return {'methodName': 'generateFoodValidationTask', 'itemId': itemId} #replace this
