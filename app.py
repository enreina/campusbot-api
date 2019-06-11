from flask import request
from flask_cors import CORS
from flask_api import FlaskAPI
from flask_api.decorators import set_renderers
from flask_api.renderers import HTMLRenderer
from taskassignment.placeTaskAssignment import placeTaskAssignment
from taskassignment.foodTaskAssignment import foodTaskAssignment
from taskassignment.questionTaskAssignment import questionTaskAssignment
from taskassignment.trashBinTaskAssignment import trashBinTaskAssignment
from db.firestoreClient import db
from common.constants import copywriting
import requests as externalRequests
import settings as env

app = FlaskAPI(__name__)
CORS(app)
app.register_blueprint(placeTaskAssignment)
app.register_blueprint(foodTaskAssignment)
app.register_blueprint(questionTaskAssignment)
app.register_blueprint(trashBinTaskAssignment)

@app.route('/')
def campusbot():
    return {'message': 'campusbot'}

@app.route('/task-preview')
@set_renderers(HTMLRenderer)
def taskPreview():
    item = request.args.to_dict()
    if 'description' not in item:
        item['description'] = "                                                                                                  "

    return '''<head>
    <title>{item[title]}</title>
    <meta property="og:title" content="{item[title]}"/>
    <meta property="og:image" content="{item[imageurl]}"/>
    <meta property="og:description" content="{item[description]}"/>
    <meta property="og:site_name" content="{item[itemtype]}" />
    </head>
    '''.format(item=item)

@app.route('/api/push-notification', methods=['GET', "POST"])
def pushNotification():
    if request is not None and request.method == 'GET':
        return {'methodName': 'pushNotification'}

    # get all users without current_task_list
    users = db.collection('users').get()
    postData = {
	"text": "We have some new tasks assigned to you, do you want to work on them?",
	"reply_markup": {"inline_keyboard": [
		    [{"text": copywriting.PUSH_NOTIF_RESPONSE_YES_TEXT, "callback_data": copywriting.PUSH_NOTIF_RESPONSE_YES_CALLBACK}, 
            {"text": copywriting.PUSH_NOTIF_RESPONSE_NO_TEXT, "callback_data": copywriting.PUSH_NOTIF_RESPONSE_NO_CALLBACK}]
            ]
        },
        "parse_mode": "Markdown"
    }
    counter = 0
    for user in users:
        userDict = user.to_dict()
        if 'telegramId' not in userDict:
            continue
        userId = userDict['telegramId']

        if userDict.get('hasReceivedPushNotif', False):
            # delete previous push notif
            if userDict.get('chatbotv2', False):
                deleteMessageEndpoint = env.DELETE_MESSAGE_ENDPOINT_V2
            else:
                deleteMessageEndpoint = env.DELETE_MESSAGE_ENDPOINT
            
            response = externalRequests.post(
                deleteMessageEndpoint, 
                json={'message_id': userDict.get('pushNotifMessageId', ''), 'chat_id': userId})

        postData['chat_id'] = userId
        if userDict.get('chatbotv2', False):
            response = externalRequests.post(env.SEND_MESSAGE_ENDPOINT_V2, json=postData)
        else:
            response = externalRequests.post(env.SEND_MESSAGE_ENDPOINT, json=postData)
        
        if response.status_code == 200:
            counter = counter + 1
            messageId = response.json()['result']['message_id']
            db.collection("users").document(userId).update({'hasReceivedPushNotif' : True, 'pushNotifMessageId': messageId, 'hasBlockedBot': False})
        elif response.status_code == 403 or 'blocked' in response.json()['description']:
            db.collection("users").document(userId).update({'hasBlockedBot': True})


    return {"message" : "Push notif sent to {counter} users".format(counter=counter)}

@app.route('/api/status')
def status():
    return {'status': 'OK'}


if __name__ == "__main__":
    app.run(debug=True)