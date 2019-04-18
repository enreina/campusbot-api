from flask import request
from flask_cors import CORS
from flask_api import FlaskAPI
from flask_api.decorators import set_renderers
from flask_api.renderers import HTMLRenderer
from taskassignment.placeTaskAssignment import placeTaskAssignment
from taskassignment.foodTaskAssignment import foodTaskAssignment
from taskassignment.questionTaskAssignment import questionTaskAssignment
from taskassignment.trashBinTaskAssignment import trashBinTaskAssignment

app = FlaskAPI(__name__)
CORS(app)
app.register_blueprint(placeTaskAssignment)
app.register_blueprint(foodTaskAssignment)
app.register_blueprint(questionTaskAssignment)
app.register_blueprint(trashBinTaskAssignment)

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

@app.route('/api/status')
def status():
    return {'status': 'OK'}


if __name__ == "__main__":
    app.run(debug=True)