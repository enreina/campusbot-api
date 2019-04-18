from dotenv import load_dotenv, find_dotenv
import os
load_dotenv(find_dotenv())

FIRESTORE_SERVICE_ACCOUNT_PATH = os.getenv('FIRESTORE_SERVICE_ACCOUNT_PATH')