import sys
sys.path.append('users')

from flask import Flask, request, jsonify, redirect
from flask_pymongo import PyMongo

from werkzeug.security import generate_password_hash, check_password_hash

from bson import json_util

from config import MONGO_URI

from put_users import put_users

app = Flask(__name__)
app.config['MONGO_URI'] = MONGO_URI
app.config['DEBUG'] = True

app_context = app.app_context()
app_context.push()

mongo = PyMongo(app)

col_users = mongo.db.users
col_questions = mongo.db.questions

@app.route('/', methods=['GET'])
def index():
    res = col_users.find({})
    return json_util.dumps(list(res)), 200

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    data['password'] = generate_password_hash(data['password'])
    col_users.insert_one(data)
    return 'usuario ' + data['username'] + ' criado.', 201

@app.route('/users/<username>', methods=['GET'])
def get_user(username):
    res_get = col_users.find_one({'username': username})
    if res_get == None: 
        return 'Usuário não encontrado', 404
    else:
        return json_util.dumps(list(res_get)), 200

# rota para exemplificar como utilizar obter variaveis
# de url. teste acessando 
# http://localhost:8088/questions/search?disciplina=BancoDeDados 
@app.route('/questions/search', methods=['GET'])
def search():
    disciplina = request.args.get('disciplina')
    return disciplina, 200
