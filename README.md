# campusbot-api

1. Clone the repo to your local directory, e.g:
```
git clone git@github.com:enreina/campusbot-api.git
```

2. Install python (if you haven't) along with `pip` and `virtualenv`

```
sudo apt-get install python2.7
sudo apt-get install python-pip python-dev build-essential 
sudo pip install --upgrade pip
sudo pip install --upgrade virtualenv 
```
3. Create and activate a python virtual environment
```
cd /home/ubuntu/hcbot
mkdir venv
virtualenv ./venv
source ./venv/bin/activate
```
4. Install requirements
```
pip install -r requirements.txt
```
5. Create `.env` file with Firestore credentials and push notif message endpoint
```
FIRESTORE_SERVICE_ACCOUNT_PATH = '/Users/enreina/thesis-projects/campusbot-b7b7f-firebase-adminsdk-8glnq-1610672393.json'
```
6. Allow port 5000 (you can skip this if you are running on local installation)
```
sudo ufw allow 5000
```
7. Run the app
```
python app.py
```
8. Open the api status to make sure it is running
http://127.0.0.1:5000/api/status

9. Expose the url to public network using ngrok. Download ngrok [here](https://ngrok.com/download) and follow the instruction to sign up and set up (if you haven't done so). Then run ngrok to expose the API:

```
./ngrok http 5000
```
Copy the public url and use it to set the `CAMPUSBOT_BASE_URL` in the `.env` file of your local [campusbot](https://github.com/enreina/campusbot) installation.


### ENDPOINTS
The endpoints are live on `campusbot.cf`
* `GET /api/status`
* `POST /api/[place|trashbin]/generate-enrichment-task`
* `POST /api/[food|place|question|trashbin]/generate-enrichment-task/<itemId>`
* `POST /api/[food|place|question|trashbin]/generate-validation-task/<userId>/<enrichmentTaskInstanceId>`
* `POST /api/[food|place|question|trashbin]/assign-task/<taskId>`
* `POST /api/[food|place|question|trashbin]/assign-task-to-user/<userId>`

### Deployment to production
1. ssh to deployment server
2. Move to directory
```
cd /data/campusbot-api
```
3. Pull the newest source code of master branch
```
git pull
```
4. If asked, provide passphrase of deploy key
5. Restart gunicorn process of this app
```
sudo systemctl restart campusbot-api
```
6. Test the endpoint `campusbot.cf/api/status`



   
