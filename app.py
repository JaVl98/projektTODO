#knihovny
import json
from flask import Flask, request, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_api import status
import jwt

from functools import wraps
from datetime import datetime, timedelta

#autorizace uzivatele pomoci JWT
SECRET_KEY = "lkdajc049dfnLSKFJ38FOIJEJFPA48FU40U8JLJSAKJDSLAKJklk"
JWT_SECRET = "sak3f4oufpfojprdovasporgvkjpojgvpoavjproksada3#$$SSK"

#vytvoreni flask appky, vytvoreni databaze
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.sqlite'

db = SQLAlchemy(app)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazev_ukolu = db.Column(db.String(30))
    popis_ukolu = db.Column(db.String(500))
    status_ukolu = db.Column(db.Boolean, default=True)

@app.before_first_request
def create_tables(): 
    db.create_all()

#autorizacni middleware, definovany pomoc dekoratoru => autentizace 
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("x-access-token", None)
        if not token:
            return jsonify({"message": "Autentizační token chybí!"}), 401

        try:
            jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.DecodeError:
            return jsonify({"message": "Autentizační token je chybný!"}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Autentizační token vypršel!"}), 401

        return f(*args, **kwargs)

    return decorated

#GET jako autorizace uzivatele
#generovani JWT tokenu, pro praci v Postmanu, potreba SECRET_KEY uzivatele, ktery se posila do headers HTTP
@app.route("/auth", methods=["GET"])
def authorize():
    user_key = request.headers.get('x-user-key', None)
    if user_key == SECRET_KEY:
        payload = {
            "user": "api",
            "exp": datetime.now() + timedelta(minutes=30),
        }
        encoded = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        return jsonify({"Token": encoded})

    else:
        payload = {"message": "Klíč je chybný!"}
        return jsonify(payload), 403


#POST jako pridani ukolu
@app.route('/task', methods=['POST'])
@token_required
def vytvoreni_ukolu():
    data = request.get_json()

    novy_ukol = Task(nazev_ukolu=data['nazev_ukolu'], popis_ukolu=data['popis_ukolu'], status_ukolu=False)

    db.session.add(novy_ukol)
    db.session.commit()

    return make_response(jsonify("Nový úkol byl přidán!"), 200)


#GET jako ziskani seznamu ukolu
@app.route('/', methods=['GET'])
def vypis_ukolu():
    filters = {
        "VSE": "all",
        "HOTOVE": "completed",
        "NEHOTOVE": "not_completed"
    }
    filter = request.args.get('filter', None)

    if filter == filters["VSE"]:
        task_query = Task.query.all()

    elif filter == filters["HOTOVE"]:
        task_query = Task.query.filter_by(status_ukolu=True).all()

    elif filter == filters["NEHOTOVE"]:
        task_query = Task.query.filter_by(status_ukolu=False).all()

    else:
        return make_response(jsonify("Daný filtr nebyl nalezen!"), 404)
    
    output = []

    for task in task_query:
        task_data = {}
        task_data['id'] = task.id
        task_data['nazev_ukolu'] = task.nazev_ukolu
        task_data['popis_ukolu'] = task.popis_ukolu
        task_data['status_ukolu'] = task.status_ukolu
        output.append(task_data)
    
    response = jsonify(
        {
            "items": output
        }
    )

    return response, status.HTTP_201_CREATED

#PUT jako uprava ukolu
@app.route('/task/<id>', methods=['PUT'])
@token_required
def uprava_ukolu(id):
    data = request.get_json()
    nazev_ukolu  = data.get('nazev_ukolu', None)
    popis_ukolu = data.get('popis_ukolu', None)
    status_ukolu = data.get('status_ukolu', None)

    task = Task.query.filter_by(id=id).first()

    if not task:
        return make_response(jsonify("Daný úkol nebyl nalezen!"), 404)
    
    task.nazev_ukolu = nazev_ukolu
    task.popis_ukolu = popis_ukolu
    task.status_ukolu = status_ukolu

    db.session.commit()

    return make_response(jsonify("Daný úkol byl aktualizován!"), 200)

#DELETE jako mazani ukolu
@app.route("/task/<id>", methods=["DELETE"])
@token_required
def smazani_ukolu(id):
    task = Task.query.filter_by(id=id).first()

    if not task:
        return make_response(jsonify("Dané ID nebylo nalezeno!"), 404)

    db.session.delete(task)
    db.session.commit()

    return make_response(jsonify("Daný úkol byl smazán!"), 200)

#DEBUG
if __name__ =='__main__':
    db.create_all()
    app.run(debug=True, port="80", host="0.0.0.0")