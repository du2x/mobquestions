
from bson import json_util

from flask_testing import TestCase
from flask_pymongo import PyMongo

from app import app

from config import MONGO_URI_TESTS




class MainTestCase(TestCase):

    TESTING = True

    def create_app(self):
        app.config['MONGO_TESTS_URI'] = MONGO_URI_TESTS
        app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
        mongo = PyMongo(app, config_prefix='MONGO_TESTS')
        self.col_users = mongo.db.users
        self.col_questions = mongo.db.questions
        self.col_tokens = mongo.db.tokens        # refresh tokens
        return app


    def setUp(self):
        with open('data.json') as f:
            data = f.read()
            file_data = json_util.loads(data)
            self.col_questions.insert_one(file_data)        


    def test_create_user(self):
        data = {'username': 'mark', 'password': '123'}
        response = self.client.post('/users', data=data, content_type='application/json')
        
        self.assertEquals(response.status_code, 201)


    def tearDown(self):
        self.col_users.delete_many({})
        self.col_questions.delete_many({})
        self.col_tokens.delete_many({})
        
    
