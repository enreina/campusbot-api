from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())

FIRESTORE_SERVICE_ACCOUNT_PATH = os.getenv('FIRESTORE_SERVICE_ACCOUNT_PATH')
SEND_MESSAGE_ENDPOINT = os.getenv('SEND_MESSAGE_ENDPOINT')
SEND_MESSAGE_ENDPOINT_V2 = os.getenv('SEND_MESSAGE_ENDPOINT_V2')
DELETE_MESSAGE_ENDPOINT = os.getenv('DELETE_MESSAGE_ENDPOINT')
DELETE_MESSAGE_ENDPOINT_V2 = os.getenv('DELETE_MESSAGE_ENDPOINT_V2')
WIKIBASE_URL = os.getenv('WIKIBASE_URL')
WIKIBASE_PASSWORD_SALT = os.getenv('WIKIBASE_PASSWORD_SALT')
WIKIBASE_BOT_USERNAME = os.getenv('WIKIBASE_BOT_USERNAME')
WIKIBASE_BOT_PASSWORD = os.getenv('WIKIBASE_BOT_PASSWORD')