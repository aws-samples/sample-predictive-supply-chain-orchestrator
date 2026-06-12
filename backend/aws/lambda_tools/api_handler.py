"""
Lambda handler for the Flask API behind API Gateway.
Uses apig-wsgi to adapt Flask/WSGI to Lambda event format.
"""

from apig_wsgi import make_lambda_handler
from api.server import app

handler = make_lambda_handler(app)
