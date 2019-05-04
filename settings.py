from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())

FIRESTORE_SERVICE_ACCOUNT_PATH = os.getenv('FIRESTORE_SERVICE_ACCOUNT_PATH')
SEND_MESSAGE_ENDPOINT = os.getenv('SEND_MESSAGE_ENDPOINT')
DELETE_MESSAGE_ENDPOINT = os.getenv('DELETE_MESSAGE_ENDPOINT')