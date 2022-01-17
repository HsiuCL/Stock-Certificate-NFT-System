import flask
import os
import sqlite3
import uuid
import smtplib, ssl
import subprocess
import requests
import json
from flask import Flask, session, render_template, request, redirect, url_for, send_file, flash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from scripts.collectible.collectible_helper import deploy_collectible
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime as dt


app = flask.Flask(__name__)
app.config['DATABASE'] = 'static/datas/userdata.db'
app.config['SECRET_KEY'] = os.urandom(24)


csrf = CSRFProtect(app)


@app.route('/')
def mainpage():
    con = sqlite3.connect(app.config['DATABASE'])
    cur = con.cursor()
    cur.execute("SELECT id, name FROM users")
    users_raw = cur.fetchall()
    con.close()
    users = []
    for user in users_raw:
        users.append({
            'id': user[0],
            'image': f'static/datas/{user[0]}/logo.jpg',
            'name': user[1]
            })
    return render_template('mainpage.html', users=users)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        company_name = request.form['company_name']
        company_symbol = request.form['company_symbol']
        min_signature = request.form['min_signature']
        member_account = request.form.getlist('member_account')
        image = request.files['image']
        try:
            image_path = f'static/datas/tmp/{str(uuid.uuid4())}.jpg'
            image.save(image_path)
            output = deploy_collectible(company_name, company_symbol, member_account, min_signature, image_path)
            con = sqlite3.connect(app.config['DATABASE'])
            cur = con.cursor()
            new_id = output.decode('utf-8').split('\n')[-3][36:78]
            cur.execute("INSERT INTO users (id, name, symbol, collection_url) VALUES (?, ?, ?, ?)", [new_id, company_name, company_symbol, 0])
            con.commit()
            con.close()
            os.mkdir(f'static/datas/{new_id}')
            os.replace(image_path, f'static/datas/{new_id}/logo.jpg')
            return redirect(url_for('set_collection', company_name=company_name))
        except Exception as e:
            print(e)
 
    return render_template('register.html')

@app.route('/set_collection', methods=['GET', 'POST'])
def set_collection(company_name=''):
    company_name = request.args.get("company_name", company_name)
    if request.method == 'POST':
        company_name = request.form['company_name']
        collection_url = request.form['collection_url']
        con = sqlite3.connect(app.config['DATABASE'])
        cur = con.cursor()
        cur.execute("UPDATE users SET collection_url = (?) WHERE name == (?)", [collection_url, company_name])
        con.commit()
        con.close()
        return redirect(url_for('mainpage'))

    return render_template('set_collection.html', company_name=company_name)

def pin_to_IPFS(user_id, image_path, company_name, company_symbol, timestamp, number_of_shares, certificate_type):
    def _pin_to_IPFS(filename):
        ipfs_handler_path = './scripts/IPFS/ipfs_handler.js'
        cmd = os.popen(f'node -e \'require("{ipfs_handler_path}").ipfs_pin_file("{filename}")\'')
        result = cmd.read()
        cmd.close()
        return result

    image_hash = _pin_to_IPFS(image_path)
    if len(image_hash) != 47:
        print('Error occured when pinning image to ipfs.')
        print(image_hash)
        return
    image_hash = image_hash[:-1]

    attributes = [
            {'trait_type': 'Company Name', 'value': company_name},
            {'trait_type': 'Company Symbol', 'value': company_symbol},
            {'trait_type': 'Timestamp', 'value': timestamp},
            {'trait_type': 'Number Of Shares', 'value': number_of_shares},
            {'trait_type': 'Certificate Type', 'value': certificate_type}
        ]
    
    operation_name = f'{certificate_type} {number_of_shares} Shares Of {company_name}({company_symbol}) Stock'

    metadata = {
            'name': operation_name,
            'image': f'https://ipfs.io/ipfs/{image_hash}',
            'attributes': attributes
        }
    metadata_file = f'static/datas/{user_id}/{str(uuid.uuid4())}.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f)
    metadata_hash = _pin_to_IPFS(metadata_file)
    return metadata_hash
    
@app.route('/set_up_IPFS', methods=['GET','POST'])
def set_up_IPFS():
    operation = request.form['operation']
    user_id = request.form['user_id']
    con = sqlite3.connect(app.config['DATABASE'])
    cur = con.cursor()
    cur.execute("SELECT name, symbol FROM users WHERE id == (?)", [user_id])
    data_raw = cur.fetchone()
    company_name, company_symbol = data_raw[0], data_raw[1]
    con.close()
    
    if operation == 'founding':
        founding_amount = request.form['founding_amount']
        founding_image = request.files['founding_image']
        founding_image_path = f'static/datas/{user_id}/{str(uuid.uuid4())}.jpg'
        founding_image.save(founding_image_path)
        hash_val = pin_to_IPFS(user_id, founding_image_path, company_name, company_symbol, str(dt.now()), founding_amount, 'Founding')
        return {'uri_1': f'https://ipfs.io/ipfs/{hash_val}', 'uri_2': ''}
    elif operation == 'issue':
        issue_amount = request.form['issue_amount']
        issue_image = request.files['issue_image']
        issue_image_path = f'static/datas/{user_id}/{str(uuid.uuid4())}.jpg'
        issue_image.save(issue_image_path)
        hash_val = pin_to_IPFS(user_id, issue_image_path, company_name, company_symbol, str(dt.now()), issue_amount, 'Issue')
        return {'uri_1': f'https://ipfs.io/ipfs/{hash_val}', 'uri_2': ''}
    elif operation == 'burn_one_issue_two':
        b1i2_issue_amount_1 = request.form['b1i2_issue_amount_1']
        b1i2_image_1 = request.files['b1i2_image_1']
        b1i2_image_path_1 = f'static/datas/{user_id}/{str(uuid.uuid4())}.jpg'
        b1i2_image_1.save(b1i2_image_path_1)
        hash_val_1 = pin_to_IPFS(user_id, b1i2_image_path_1, company_name, company_symbol, str(dt.now()), b1i2_issue_amount_1, 'Issue')
        b1i2_issue_amount_2 = request.form['b1i2_issue_amount_2']
        b1i2_image_2 = request.files['b1i2_image_2']
        b1i2_image_path_2 = f'static/datas/{user_id}/{str(uuid.uuid4())}.jpg'
        b1i2_image_2.save(b1i2_image_path_2)
        hash_val_2 = pin_to_IPFS(user_id, b1i2_image_path_2, company_name, company_symbol, str(dt.now()), b1i2_issue_amount_2, 'Issue')
        return {'uri_1': f'https://ipfs.io/ipfs/{hash_val_1}', 'uri_2': f'https://ipfs.io/ipfs/{hash_val_2}'}

@app.route('/userpage')
def userpage():
    preselect_content = request.args.get('preselect_content', 'collection')
    user_id = request.args.get('user_id')

    con = sqlite3.connect(app.config['DATABASE'])
    cur = con.cursor()
    cur.execute("SELECT name, collection_url, symbol FROM users WHERE id == (?)", [user_id])
    user_data_raw = cur.fetchone()
    con.close()

    user_abi = []
    with open(f'build/deployments/4/{user_id}.json') as f:
        user_deploy_raw = json.loads(f.read())
        user_abi = user_deploy_raw['abi']

    if user_data_raw[1] == '0':
        collection_url = '0'
    elif '?' in user_data_raw[1]:
        collection_url = f'{user_data_raw[1]}&embed=true'
    else:
        collection_url = f'{user_data_raw[1]}?embed=true'
    user_data = {'name': user_data_raw[0], 'collection_url': collection_url, 'symbol': user_data_raw[2]}

    return render_template('userpage.html', user_data=user_data, preselect_content=preselect_content, user_id=user_id, user_abi=user_abi, WEB3_INFURA_PROJECT_ID=os.environ['WEB3_INFURA_PROJECT_ID'])


if __name__ == '__main__':
    with open('.env') as f:
        env_list = f.read().split('\n')
        for env in env_list:
            env = env[7:].split('=')
            if len(env) == 2:
                env_name, env_value = env[0], env[1]
                os.environ[env_name] = env_value
    app.config['SYSTEM_ADDRESS'] = os.environ['SYSTEM_ADDRESS']

    app.run(host="0.0.0.0",
            port=int("8888"),
            debug=True)
