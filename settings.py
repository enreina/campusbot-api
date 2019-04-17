from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())

PORT = int(os.getenv('CAMPUSBOT_API_PORT'))
FIRESTORE_SERVICE_ACCOUNT_PATH = os.getenv('FIRESTORE_SERVICE_ACCOUNT_PATH')