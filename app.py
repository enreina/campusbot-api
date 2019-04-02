from flask import request
from flask_api import FlaskAPI
from flask_api.decorators import set_renderers
from flask_api.renderers import HTMLRenderer

app = FlaskAPI(__name__)

@app.route('/task-preview')
@set_renderers(HTMLRenderer)
def taskPreview():
    return '''<head>
    <title>{item[title]}</title>
    <meta property="og:title" content="{item[title]}"/>
    <meta property="og:image" content="{item[imageurl]}"/>
    <meta property="og:site_name" content="{item[itemtype]}" />
    </head>
    '''.format(item=request.args)

if __name__ == "__main__":
    app.run(debug=True)