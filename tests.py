
from bson import json_util

from flask_testing import TestCase

from pymongo import MongoClient

from app import app

from config import MONGO_URI_TESTS




class MainTestCase(TestCase):

    TESTING = True

    def create_app(self):
        app.config['MONGO_TESTS_URI'] = MONGO_URI_TESTS
        app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
        app_context = app.app_context()
        app_context.push()        
        return app


    def setUp(self):
        client = MongoClient(MONGO_URI_TESTS)
        db = MONGO_URI_TESTS.split('/')[-1]
        self.col_users = client[db].users
        self.col_questions = client[db].questions
        self.col_tokens = client[db].tokens        # refresh tokens        
        with open('data.json') as f:
            data = f.read()
            file_data = json_util.loads(data)
            self.col_questions.insert_one(file_data)


    def test_create_user(self):
        data = {'username': 'mark', 'name': 'Mark', 'password': '123', 'email':'mark@gmail.com'}
        response = self.client.post('/users', 
                                    data=json_util.dumps(data), 
                                    content_type='application/json')
        self.assertEquals(response.status_code, 201)

    
    def test_create_duplicate_user(self):
        data = {'username': 'mark', 'name': 'Markowsk', 'password': 'abs3', 'email':'mark@gmail.com'}
        response = self.client.post('/users', 
                                    data=json_util.dumps(data), 
                                    content_type='application/json')
        self.assertEquals(response.status_code, 409) # veja https://stackoverflow.com/questions/3825990/http-response-code-for-post-when-resource-already-exists


    def test_get_user(self):
        response = self.client.get('/users/mark')
        self.assertEquals(response.status_code, 200)


    def tearDown(self):
        # apagar todos registros
        self.col_users.delete_many({})
        self.col_questions.delete_many({})
        self.col_tokens.delete_many({})
