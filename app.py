from flask import Flask, request, jsonify, redirect, g
from flask_pymongo import PyMongo

from werkzeug.security import generate_password_hash, check_password_hash

from bson import json_util

from config import MONGO_URI, MONGO_URI_TESTS, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

from auth import *

import os
import redis

rcache = redis.Redis(
            host=REDIS_HOST, 
            port=REDIS_PORT,
            password=REDIS_PASSWORD)


def create_app(testing = False):
    app = Flask(__name__)
    if os.getenv('FLASK_TESTING') and os.getenv('FLASK_TESTING')=='1':
        app.config['MONGO_URI'] = MONGO_URI_TESTS
    else:
        # app.config['MONGO_URI'] = MONGO_URI_TESTS
        app.config['MONGO_URI'] = MONGO_URI
    app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
    app_context = app.app_context()
    app_context.push()        
    return app

mongo = None
app = create_app()
mongo = PyMongo(app)

col_users = mongo.db.users
col_questions = mongo.db.questions
col_tokens = mongo.db.tokens        # refresh tokens
col_answers = mongo.db.answers


def authenticate(username, password):
    user = col_users.find_one({'username': username})
    if user and check_password_hash(user['password'], password):
        return user
    else:
        return None


def int_try_parse(value):
    try:
        return int(value)
    except ValueError:
        return value


@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    user = authenticate(data['username'], data['password'])

    if user:
        token_payload = {'username': user['username']}
        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token(token_payload)
        col_tokens.insert_one({'value': refresh_token})
        response = json_util.dumps({'access_token': access_token, 
                                    'refresh_token': refresh_token})
        return response
    else:
        return "Unauthorized", 401


@app.route('/', methods=['GET'])
@jwt_required
def index():
    res = col_users.find({})
    return json_util.dumps(list(res)), 200


@app.route('/refresh_token', methods=['GET'])
@jwt_refresh_required
def refresh_token():    
    token = col_tokens.find_one({'value': g.token})
    if token:
        col_tokens.delete_one({'value': g.token})
        token_payload = {'username': g.parsed_token['username']}
        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token(token_payload)
        col_tokens.insert_one({'value': refresh_token})
        return json_util.dumps({'access_token': access_token, 
                                'refresh_token': refresh_token}), 200
    else:
        return "Unauthorized", 401


# rota para visualizar o conteudo do payload encriptado no token.
@app.route('/token', methods=['GET'])
@jwt_required
def token():    
    return json_util.dumps(g.parsed_token), 200


@app.route('/v1/users', methods=['POST'])
def create_user():
    data = request.get_json()

    if 'password' not in data.keys() or 'username' not in data.keys():
        return 'Bad Request', 400

    username = data['username']
    
    user = col_users.find_one({'username': username}, {'_id': 0, 'username': 1})

    if user is None:
        data['password'] = generate_password_hash(data['password'])
        col_users.insert_one(data)
        return 'usuario ' + data['username'] + ' criado.', 201
    else:
        return 'usuario ' + data['username'] + ' já existe.', 409 #alterei o codigo de retorno de 200 para 409


@app.route('/v1/users/<username>', methods=['GET'])
def get_user(username):
    res_get = col_users.find_one({'username': username}, {'_id': 0, 'password': 0})
    if res_get == None: 
        return 'Usuário não encontrado', 404
    else:
        return json_util.dumps(res_get), 200


@app.route('/v1/users/<username>', methods=['PUT'])
@jwt_required
def put_user(username):
    data = request.get_json()
    user = {}

    if data.get('email', None) is not None:
        user['email'] = data['email']
    if data.get('name', None) is not None:
        user['name'] = data['name']
    if data.get('phones', None) is not None:
        user['phones'] = data['phones']
    
    if user == {}:
        return 'bad request', 400
    else:
        col_users.update_one({'username': username}, {'$set': user})
        return 'usuario ' + username + ' atualizado.', 200


@app.route('/v1/authenticate', methods=['POST'])
def authenticate_user():
    data = request.get_json()
    user = col_users.find_one({'username': data['username']})
    if  'username' in data.keys() and 'password' in data.keys(): 
        if user  == None: 
            return 'Dados não enviados corretamente', 403
        else: 
            if check_password_hash(user['password'], data['password']) == True:
                return 'Usuário autenticado com sucesso', 200
            else: 
                return 'Dados não enviados corretamente', 403
    else:
        return 'Dados não enviados corretamente', 400


@app.route('/v1/users/<username>', methods=['PATCH']) 
def patch_password(username):
    data = request.get_json()
    user = {}
    if data.get('password', None) is not None:
        user['password'] = generate_password_hash(data['password'])    
    if user == {}:
        return 'bad request', 400
    else:
        col_users.update_one({'username': username}, {'$set': user})
        return 'Senha do usuário ' + username + ' atualizada.', 200


@app.route('/v1/questions/search', methods=['GET'])
def search():
    args = request.args.to_dict()
    if 'disciplina' in args:
        args['disciplina'] = int_try_parse(args['disciplina'])
    if 'ano' in args:
        args['ano'] = int_try_parse(args['ano'])

    questions = col_questions.find(args)
    return json_util.dumps(list(questions)), 200


@app.route('/v1/questions/<question_id>', methods=['GET'])
def get_question(question_id):
    res_get = col_questions.find_one({'id': question_id})
    if res_get == None: 
        return 'Questão não encontrada', 404
    else:
        return json_util.dumps(res_get), 200


@app.route('/v1/questions/<question_id>/comment', methods=['POST'])
@jwt_required
def insert_comment(question_id):
    data = request.get_json()
    questao = col_questions.find_one({'id': question_id})
    user = col_users.find_one({'username': data['username']})
    comment = {}
    comment['username'] = data['username']
    comment['message'] = data['message']
    if  'username' in data.keys() and 'message' in data.keys(): 
        if user  == None: 
            return 'Dados não enviados corretamente', 401
        else: 
            if questao == None:
                return 'Dados não enviados corretamente', 404
            else:
                col_questions.update_one({'id': question_id}, {'$set': comment}), 200
                return "Questão atualizada com sucesso!"
    else:
        return 'Dados não enviados corretamente', 401


@app.route('/v1/questions/<question_id>/answer', methods=['POST'])
@jwt_required
def insert_answer(question_id):
    data = request.get_json()
    jwt = g.parsed_token
    userAnswer = data['answer'].upper()
    print(data)
    answer = col_answers.find_one({'id': question_id, 'username': jwt['username']})

    if answer is None:
        question = col_questions.find_one({'id': question_id}, {'_id': 0, 'resposta': 1})
        answer_is_correct = True if userAnswer == question['resposta'] else False
        
        answer = {
            'id': question_id,
            'username': jwt['username'],
            'answer': userAnswer,
            'answer_is_correct': answer_is_correct
        }
        
        col_answers.insert_one(answer)
        col_questions.update_one({'id': question_id}, {'$inc': {'answersNumber': 1}})

        if answer_is_correct:
            return 'Resposta Correta.', 200
        else:
            return 'Resposta Incorreta.', 200
    else:
        return 'Resposta já registrada.', 203


@app.route('/v1/questions/answer', methods=['GET'])
@jwt_required
def get_answer():
    print('test')
    jwt = g.parsed_token
    answers = list(col_answers.find({'username': jwt['username']}, {'_id': 0, 'id': 1, 'answer': 1}))
    
    if len(answers) > 0:
        return json_util.dumps(answers), 200
    else:
        return 'Not Found', 404


@app.route('/v1/featured_questions', methods=['POST'])
def set_featured_questions():
    featured_questions = col_questions.find({}).sort([('answersNumber', DESCENDING)]).limit(10)
    rcache.set('featured_questions', json_util.dumps(list(featured_questions)))
    return 'Cache updated', 200


@app.route('/v1/featured_questions', methods=['GET'])
def get_featured_questions():
    featured_questions = rcache.get('featured_questions')
    if featured_questions is not None:
        return featured_questions, 200
    else:
        featured_questions = list(col_questions.find({}).sort([('answersNumber', DESCENDING)]).limit(10))
        rcache.set('featured_questions', json_util.dumps(featured_questions))
        return json_util.dumps(featured_questions), 200