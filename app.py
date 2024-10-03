from flask import Flask, render_template, url_for, session, redirect, flash
from flask_bootstrap import Bootstrap
from flask_moment import Moment

from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length

import os
from datetime import datetime
from utils.constants import *
import random
from environs import Env


env = Env()
env.read_env()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY_FLASK')

bootstrap = Bootstrap(app)
moment = Moment(app)
N_RANDOM = random.randint(7, 300)


def preprocess_text(some_text: str):
    some_text_processed = ' '.join([word for word in some_text.split(' ') if len(word)])
    return some_text_processed


def run_model(original_text, suspect_text):
    import json
    import requests

    API_URL = os.environ.get('API_URL')
    API_TOKEN = os.environ.get('API_TOKEN')
    # print(f'\nAPI_URL:\n{API_URL}\n\nAPI_TOKEN:\n{API_TOKEN}\n')
    headers = {'Authorization': f'Bearer {API_TOKEN}'}
    payload = {'inputs': {'source_sentence': original_text, 'sentences': [suspect_text]}}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        res = response.json()
    except Exception as e:
        res = [-1*random.randint(0, 100)/100] # for tests
        print(f'\nErro:\n{e}\n')
    # print(f'res:\n{res}')

    return res


def check_plagiarism(original_text: str, suspect_text: str):
    is_fake = False    
    
    original_text_clean = preprocess_text(original_text)
    suspect_text_clean = preprocess_text(suspect_text)

    plagiarism_res = run_model(original_text_clean, suspect_text_clean)

    print(f'\nplagiarism_res:\n{plagiarism_res}  |  type(plagiarism_res): {type(plagiarism_res)}\n')
    
    N_MAX_RETRY = 3
    n_retry = 1    
    if type(plagiarism_res) == dict:
        while 'error' in plagiarism_res.keys():
            import time
            print(f'\nErro:\n{plagiarism_res["error"]}')
            time_waiting = 0.7*plagiarism_res["estimated_time"]
            print(f'[{n_retry}] Nova tentativa - esperando {time_waiting} s [{plagiarism_res["estimated_time"]}]')
            time.sleep(time_waiting)
            plagiarism_res = run_model(original_text_clean, suspect_text_clean)
            n_retry += 1
            if n_retry >= N_MAX_RETRY:
                plagiarism_probab = 0.0
                break
            if type(plagiarism_res) != dict:
                plagiarism_probab = plagiarism_res[0]
                break
    else:
        plagiarism_probab = plagiarism_res[0]
        # print(f'\nplagiarism_probab: {plagiarism_probab}\n')

    return round(plagiarism_probab, 2)


class NameForm(FlaskForm):
    original_text = TextAreaField('Texto Original', 
        validators=[InputRequired(), Length(7, 1000)],
        render_kw={'class': 'form-control', 'rows':5, 
        'placeholder': '\nEntre com um texto aqui. Por ex.:\n' + LOREM_IPSUM[:N_RANDOM] + ' ...'})

    suspect_text = TextAreaField('Texto Suspeito de Plágio',
        validators=[InputRequired(), Length(7, 1000)],
        render_kw={'class': 'form-control', 'rows':4,
        'placeholder': '\nEntre com outro texto aqui.'})
        
    submit = SubmitField('Checar')


@app.route('/', methods=['GET', 'POST'])
def index():
    # print(f'{len(LOREM_IPSUM)}')
    form = NameForm()
    is_fraud = -1

    session['original_text'] = form.original_text.data
    session['suspect_text'] = form.suspect_text.data

    if form.validate_on_submit():
        original_text = session.get('original_text')
        suspect_text = session.get('suspect_text')
        # print(f'\n original_text: {original_text} \n')
        # print(f'\n suspect_text: {suspect_text} \n')        
        plagiarism_probab = check_plagiarism(original_text, suspect_text)
        # print(f'\nplagiarism_probab: {plagiarism_probab}\n')
        
        # for tests
        emph = ""
        if plagiarism_probab < 0:
            plagiarism_probab *= -1
            emph = '"'
        # check probab
        if plagiarism_probab > 0.5:
            is_fraud = 1
            print('Parece plágio!')
        elif plagiarism_probab >= 0:
            is_fraud = 0
            print('Não parece plágio!')
        print(f'\nTexto {emph}checado{emph}! {emph}Probabilidade de plágio{emph} = {plagiarism_probab*100:.2f} %.\n')
        flash(f'\nTexto {emph}checado{emph}! {emph}Probabilidade de plágio{emph} = {plagiarism_probab*100:.2f} %.\n')
        
        # return redirect(url_for('index'))
        return render_template('index.html', form=form, 
            user_name=session.get('original_text'), current_time=datetime.utcnow(),
            is_fraud=is_fraud)
        
    return render_template('index.html', form=form, 
        user_name=session.get('original_text'), current_time=datetime.utcnow(),
        is_fraud=is_fraud)


@app.route('/how_to')
def how_to():
    return render_template('how_to.html', current_time=datetime.utcnow())


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', error=e), 404


if __name__ == '__main__':
    app.run(debug=True)