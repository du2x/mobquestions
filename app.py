from flask import Flask, request, jsonify, redirect, g
from flask_pymongo import PyMongo

from werkzeug.security import generate_password_hash, check_password_hash

from bson import json_util

from config import MONGO_URI
from auth import *


app = Flask(__name__)
app.config['MONGO_URI'] = MONGO_URI
app.config['DEBUG'] = True

app_context = app.app_context()
app_context.push()

mongo = PyMongo(app)

col_users = mongo.db.users
col_questions = mongo.db.questions
col_tokens = mongo.db.tokens        # refresh tokens


def authenticate(username, password):
    user = col_users.find_one({'username': username})
    if user and check_password_hash(user['password'], password):
        return user
    else:
        return None

@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    user = authenticate(data['username'], data['password'])
    if user:
        token_payload = {'username': user['username']}
        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token(token_payload)
        col_tokens.insert_one({'value': refresh_token})
        return jsonify({'access_token': access_token, 
                        'refresh_token': refresh_token})
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
    username = data['username']
    
    user = col_users.find_one({'username': username}, {'_id': 0, 'username': 1})

    if user is None:
        data['password'] = generate_password_hash(data['password'])
        col_users.insert_one(data)
        return 'usuario ' + data['username'] + ' criado.', 201
    else:
        return 'usuario ' + data['username'] + ' já existe.', 203

@app.route('/v1/users/<username>', methods=['GET'])
def get_user(username):
    res_get = col_users.find_one({'username': username}, {'_id': 0, 'password': 0})
    if res_get == None: 
        return 'Usuário não encontrado', 404
    else:
        return json_util.dumps(res_get), 200

@app.route('/v1/users/<username>', methods=['PUT'])
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

# rota para exemplificar como utilizar obter variaveis
# de url. teste acessando 
# http://localhost:8088/questions/search?disciplina=BancoDeDados 
@app.route('/v1/questions/search', methods=['GET'])
def search():
    disciplina = request.args.get('disciplina')
    return disciplina, 200

@app.route('/v1/authenticate', methods=['POST'])
def authenticate():
    data = request.get_json()
    user = col_users.find_one({'username': data['username']})
    if  'username' in data.keys() and 'password' in data.keys(): 
        if user  == None: 
            return 'Dados não enviados corretamente', 403
        else: 
            if check_password_hash(user['password'], data['password']) == True:
                return 'Usuário autenicado com sucesso', 200
            else: 
                return 'Dados não enviados corretamente', 403
    else:
        return 'Dados não enviados corretamente', 400
