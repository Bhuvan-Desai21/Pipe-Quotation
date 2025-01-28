from serverless_wsgi import handle_request
from app import app  # Import your Flask app

def handler(request, context):
    return handle_request(app, request, context)