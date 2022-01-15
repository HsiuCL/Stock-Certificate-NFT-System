import flask
import os
import sqlite3
import uuid
import smtplib, ssl
import subprocess
from flask import Flask, session, render_template, request, redirect, url_for, send_file, flash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from scripts.collectible.collectible_helper import deploy_collectible, create_collectible, burn_collectible
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime as dt


app = flask.Flask(__name__)
app.config['DATABASE'] = 'static/datas/userdata.db'
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SYSTEM_ADDRESS'] = '0x64FC16aeFe6d806c7527C3E22286856d63971A2C'


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
        founding_date = request.form['founding_date']
        original_number_of_shares = request.form['original_number_of_shares']
        WEB3_INFURA_PROJECT_ID = request.form['WEB3_INFURA_PROJECT_ID']
        member_name = request.form.getlist('member_name')
        member_email = request.form.getlist('member_email')
        image = request.files['image']
        if int(original_number_of_shares) > 0:
            try:
                os.environ['WEB3_INFURA_PROJECT_ID'] = WEB3_INFURA_PROJECT_ID
                deploy_collectible(company_name, company_symbol)
                os.environ['WEB3_INFURA_PROJECT_ID'] = ''
                con = sqlite3.connect(app.config['DATABASE'])
                cur = con.cursor()
                new_id = str(uuid.uuid4())
                image_name = 'logo.jpg'
                cur.execute("INSERT INTO users (id, name, symbol, founding_date, WEB3_INFURA_PROJECT_ID, collection_url) VALUES (?, ?, ?, ?, ?, ?)", [new_id, company_name, company_symbol, founding_date, WEB3_INFURA_PROJECT_ID, 0])
                con.commit()
                con.close()

                os.mkdir(f'static/datas/{new_id}')
                image.save(f'static/datas/{new_id}/{image_name}')
                con = sqlite3.connect(f'static/datas/{new_id}/localdata.db')
                cur = con.cursor()
                cur.execute("CREATE TABLE board (member TEXT PRIMARY KEY, email TEXT NOT NULL, key TEXT NOT NULL)")
                cur.execute("CREATE TABLE proposal (id INTEGER PRIMARY KEY NOT NULL, operation TEXT NOT NULL, state TEXT NOT NULL, proposer TEXT NOT NULL, rejecter TEXT, timestamp REAL NOT NULL)")
                con.commit()
                con.close()

                for cur_name, cur_email in zip(member_name, member_email):
                    try:
                        cur_key = str(uuid.uuid4())
                        hashed_key = generate_password_hash(cur_key)

                        sender_email = 'alicebob0211@gmail.com'
                        receiver_email = cur_email
                        message = f"""\
                                Subject: Your Key For \"{company_name}\" On Stock Certificate NFT System.

                                This is your (temporary) key for \"{company_name}\" on SCS.
                                You're now a member of the board for the company.
                                Key: {cur_key}"""

                        con = sqlite3.connect(f'static/datas/{new_id}/localdata.db')
                        cur = con.cursor()
                        cur.execute("INSERT INTO board (member, email, key) VALUES (?, ?, ?)", [cur_name, cur_email, hashed_key])
                        con.commit()
                        con.close()

                        port = 465
                        email_password = os.environ['EMAIL_PASSWORD']
                        context = ssl.create_default_context()
                        with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
                            server.login(sender_email, email_password)
                            server.sendmail(sender_email, receiver_email, message)
                    except Exception as e:
                        print(e)
                
                attributes = {
                        'company_name': company_name,
                        'company_symbol': company_symbol,
                        'founding_date': founding_date,
                        'number_of_shares': original_number_of_shares
                        }
                os.environ['WEB3_INFURA_PROJECT_ID'] = WEB3_INFURA_PROJECT_ID
                create_collectible('genesis', f"The genesis block of {company_name}'s stock certificate.", f'static/datas/{new_id}/{image_name}', attributes, app.config['SYSTEM_ADDRESS'])
                os.environ['WEB3_INFURA_PROJECT_ID'] = ''
                return redirect(url_for('set_collection'))
            except Exception as e:
                os.environ['WEB3_INFURA_PROJECT_ID'] = ''
                print(e)
 
    return render_template('register.html')

@app.route('/set_collection', methods=['GET', 'POST'])
def set_collection(company_name=''):
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

def execute_approved_proposal(company_id, proposal_id):
    con = sqlite3.connect(f'static/datas/{company_id}/localdata.db')
    cur = con.cursor()
    cur.execute("SELECT operation FROM proposal WHERE id == (?)", [proposal_id])
    operation = cur.fetchone()[0].split('|')
    con.close()

    con = sqlite3.connect(app.config['DATABASE'])
    cur = con.cursor()
    cur.execute("SELECT name, symbol, WEB3_INFURA_PROJECT_ID FROM users WHERE id == (?)", [company_id])
    data_raw = cur.fetchone()
    company_name, company_symbol, WEB3_INFURA_PROJECT_ID = data_raw[0], data_raw[1], data_raw[2]
    con.close()
    timestamp = str(dt.now())

    if operation[0] == 'issue':
        issue_amount, receiver, issue_image_path = operation[1], operation[2], operation[3]

        attributes = {
                'company_name': company_name,
                'company_symbol': company_symbol,
                'timestamp': timestamp,
                'number_of_shares': issue_amount 
                }
        os.environ['WEB3_INFURA_PROJECT_ID'] = WEB3_INFURA_PROJECT_ID
        create_collectible('issue', f"The certificate of issueing {issue_amount} shares to {receiver}.", issue_image_path, attributes, receiver)
        os.environ['WEB3_INFURA_PROJECT_ID'] = ''

    elif operation[0] == 'burn_one_issue_two':
        burn_id, issue_amount_1, receiver_1, image_path_1, issue_amount_2, receiver_2, image_path_2 = operation[1], operation[2], operation[3], operation[4], operation[5], operation[6], operation[7]

        os.environ['WEB3_INFURA_PROJECT_ID'] = WEB3_INFURA_PROJECT_ID
        burn_collectible(burn_id)
        os.environ['WEB3_INFURA_PROJECT_ID'] = ''
        
        attributes = {
                'company_name': company_name,
                'company_symbol': company_symbol,
                'timestamp': timestamp,
                'number_of_shares': issue_amount_1
                }
        os.environ['WEB3_INFURA_PROJECT_ID'] = WEB3_INFURA_PROJECT_ID
        create_collectible('issue', f"The certificate of issueing {issue_amount_1} shares to {receiver_1}.", image_path_1, attributes, receiver_1)
        os.environ['WEB3_INFURA_PROJECT_ID'] = ''
        
        attributes = {
                'company_name': company_name,
                'company_symbol': company_symbol,
                'timestamp': timestamp,
                'number_of_shares': issue_amount_2
                }
        os.environ['WEB3_INFURA_PROJECT_ID'] = WEB3_INFURA_PROJECT_ID
        create_collectible('issue', f"The certificate of issueing {issue_amount_2} shares to {receiver_2}.", image_path_2, attributes, receiver_2)
        os.environ['WEB3_INFURA_PROJECT_ID'] = ''

    elif operation[0] == 'burn':
        burn_id = operation[1]
        os.environ['WEB3_INFURA_PROJECT_ID'] = WEB3_INFURA_PROJECT_ID
        burn_collectible(burn_id)
        os.environ['WEB3_INFURA_PROJECT_ID'] = ''

    WEB3_INFURA_PROJECT_ID = ''


def vote_proposal(company_id, proposal_id, voter, voter_key, vote):
    if is_valid_key_pair(company_id, voter, voter_key):
        con = sqlite3.connect(f'static/datas/{company_id}/localdata.db')
        cur = con.cursor()
        cur.execute("SELECT state FROM proposal WHERE id = (?)", [proposal_id])
        state = cur.fetchone()[0]
        con.close()
        if state == 'voting':
            try:
                con = sqlite3.connect(f'static/datas/{company_id}/localdata.db')
                cur = con.cursor()
                cur.execute(f"INSERT INTO proposal_{proposal_id} (voter, vote) VALUES (?, ?)", [voter, vote])
                con.commit()
                cur.execute(f"SELECT COUNT(*) FROM proposal_{proposal_id}")
                vote_number = cur.fetchone()[0]

                if vote == 'agree':
                    cur.execute("SELECT COUNT(*) FROM board")
                    board_number = cur.fetchone()[0]
                    if vote_number == board_number:
                        cur.execute("UPDATE proposal SET state = (?) WHERE id = (?)", ['passed', proposal_id])
                        con.commit()
                        execute_approved_proposal(company_id, proposal_id)
                else:
                    cur.execute(f"UPDATE proposal SET (state, rejecter) = (?, ?) WHERE id = (?)", ['rejected', voter, proposal_id])
                    con.commit()

                con.close()
                return 'Success'
            except Exception as e:
                print(e)
        return 'Not in voting state.'
    return 'Fail'


def is_valid_key_pair(company_id, key_holder, key):
    con = sqlite3.connect(f'static/datas/{company_id}/localdata.db')
    cur = con.cursor()
    cur.execute("SELECT key FROM board WHERE member == (?)", [key_holder])
    data_raw = cur.fetchone()
    con.close()
    if data_raw != None:
        proposer_key_varification = data_raw[0]
        return check_password_hash(proposer_key_varification, key)
    return False

@app.route('/who_voted_the_proposal', methods=['GET', 'POST'])
def who_voted_the_proposal():
    user_id = request.args.get('user_id')
    proposal_id = request.args.get('proposal_id')
    con = sqlite3.connect(f'static/datas/{user_id}/localdata.db')
    cur = con.cursor()
    cur.execute(f"SELECT voter FROM proposal_{proposal_id}")
    voter_raw = cur.fetchall()
    voter = [v[0] for v in voter_raw]
    con.close()
    return render_template('who_voted_the_proposal.html', voter=voter)
    


@app.route('/userpage', methods=['GET', 'POST'])
def userpage():
    preselect_content = 'collection'
    user_id = request.args.get('user_id')

    if request.method == 'POST':
        preselect_content = 'proposal'
        form_name = request.form['form_name']
        if form_name == 'propose':
            operation = request.form['operation']
            proposer = request.form['proposer']
            proposer_key = request.form['key']
            if is_valid_key_pair(user_id, proposer, proposer_key):
                if operation == 'issue':
                    issue_amount = request.form['issue_amount']
                    receiver = request.form['receiver']
                    issue_image = request.files['issue_image']
                    issue_image_path = f'static/datas/{user_id}/{str(uuid.uuid4())}.jpg'
                    issue_image.save(issue_image_path)
                    if receiver == '':
                        receiver = app.config['SYSTEM_ADDRESS']
                    proposal_content = f'issue|{issue_amount}|{receiver}|{issue_image_path}'
                elif operation == 'burn_one_issue_two':
                    b1i2_burn_id = request.form['b1i2_burn_id']
                    b1i2_receiver_1 = request.form['b1i2_receiver_1']
                    b1i2_receiver_2 = request.form['b1i2_receiver_2']
                    b1i2_issue_amount_1 = request.form['b1i2_issue_amount_1']
                    b1i2_issue_amount_2 = request.form['b1i2_issue_amount_2']
                    b1i2_image_1 = request.files['b1i2_image_1']
                    b1i2_image_2 = request.files['b1i2_image_2']
                    b1i2_image_path_1 = f'static/datas/{user_id}/{str(uuid.uuid4())}.jpg'
                    b1i2_image_path_2 = f'static/datas/{user_id}/{str(uuid.uuid4())}.jpg'
                    b1i2_image_1.save(b1i2_image_path_1)
                    b1i2_image_2.save(b1i2_image_path_2)
                    if b1i2_receiver_1 == '':
                        b1i2_receiver_1 = app.config['SYSTEM_ADDRESS']
                    if b1i2_receiver_2 == '':
                        b1i2_receiver_2 = app.config['SYSTEM_ADDRESS']
                    proposal_content = f'burn_one_issue_two|{b1i2_burn_id}|{b1i2_issue_amount_1}|{b1i2_receiver_1}|{b1i2_image_path_1}|{b1i2_issue_amount_2}|{b1i2_receiver_2}|{b1i2_image_path_2}'
                else:
                    burn_id = request.form['burn_id']
                    proposal_content = f'burn|{burn_id}'

                con = sqlite3.connect(f'static/datas/{user_id}/localdata.db')
                cur = con.cursor()
                timestamp = str(dt.now())
                cur.execute("INSERT INTO proposal (operation, state, proposer, timestamp) VALUES (?, ?, ?, ?)", [proposal_content, 'voting', proposer, timestamp])
                con.commit()
                cur.execute("SELECT id FROM proposal WHERE proposer == (?) AND timestamp == (?)", [proposer, timestamp])
                proposal_id = cur.fetchone()[0]
                cur.execute(f"CREATE TABLE proposal_{proposal_id} (voter TEXT NOT NULL UNIQUE, vote TEXT NOT NULL)")
                con.commit()
                con.close()
                vote_proposal(user_id, proposal_id, proposer, proposer_key, 'agree')
            else:
                pass
                # alert user doesn't exist
        elif form_name == 'vote':
            proposal_id = request.form['proposal_id']
            voter = request.form['voter']
            voter_key = request.form['key']
            agreement = request.form['agreement']
            if agreement == 'agree' or agreement == 'disagree':
                if is_valid_key_pair(user_id, voter, voter_key):
                    vote_proposal(user_id, proposal_id, voter, voter_key, agreement)


    con = sqlite3.connect(app.config['DATABASE'])
    cur = con.cursor()
    cur.execute("SELECT name, collection_url, symbol FROM users WHERE id == (?)", [user_id])
    user_data_raw = cur.fetchone()
    con.close()

    con = sqlite3.connect(f'static/datas/{user_id}/localdata.db')
    cur = con.cursor()
    cur.execute("SELECT id, operation, state, timestamp, proposer, rejecter FROM proposal ORDER BY id DESC")
    proposal_raw = cur.fetchall()
    con.close()

    proposal = []
    for pps in proposal_raw:
        op = pps[1].split('|')
        operation = op[0]
        if operation == 'issue':
            proposal.append({
                'id': pps[0],
                'operation': operation,
                'issue_amount': op[1],
                'receiver': op[2],
                'image': op[3],
                'state': pps[2],
                'timestamp': pps[3],
                'proposer': pps[4],
                'rejecter': pps[5]
                })
        elif operation == 'burn_one_issue_two':
            proposal.append({
                'id': pps[0],
                'operation': operation,
                'burn_id': op[1],
                'issue_amount_1': op[2],
                'receiver_1': op[3],
                'image_1': op[4],
                'issue_amount_2': op[5],
                'receiver_2': op[6],
                'image_2': op[7],
                'state': pps[2],
                'timestamp': pps[3],
                'proposer': pps[4],
                'rejecter': pps[5]
                })
        else:
            proposal.append({
                'id': pps[0],
                'operation': operation,
                'burn_id': op[1],
                'state': pps[2],
                'timestamp': pps[3],
                'proposer': pps[4],
                'rejecter': pps[5]
                })

    if user_data_raw[1] == '0':
        collection_url = '0'
    elif '?' in user_data_raw[1]:
        collection_url = f'{user_data_raw[1]}&embed=true'
    else:
        collection_url = f'{user_data_raw[1]}?embed=true'
    user_data = {'name': user_data_raw[0], 'collection_url': collection_url, 'symbol': user_data_raw[2]}

    return render_template('userpage.html', user_data=user_data, preselect_content=preselect_content, user_id=user_id, proposal=proposal)

if __name__ == '__main__':
    with open('.env') as f:
        env_list = f.read().split('\n')
        for env in env_list:
            env = env[7:].split('=')
            if len(env) == 2:
                env_name, env_value = env[0], env[1]
                os.environ[env_name] = env_value

    app.run(host="0.0.0.0",
            port=int("8888"),
            debug=True)
