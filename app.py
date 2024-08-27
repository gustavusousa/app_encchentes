from dotenv import load_dotenv
load_dotenv()

import os
import boto3
from flask import jsonify
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash


cliente_s3 = boto3.client('s3',
                        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                        region_name=os.getenv('AWS_REGION'))

app = Flask(__name__)
app.secret_key = '51681ddd65'  # Substitua por uma string aleatória segura

def criar_banco_de_dados():
    conn = sqlite3.connect('alertas.db') 
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE, 
            senha TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario INTEGER,
            local TEXT NOT NULL,
            tipo_de_perigo TEXT NOT NULL,
            nivel_de_alerta TEXT NOT NULL,
            horario TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            url_foto_video TEXT,
            latitude REAL, 
            longitude REAL, 
            FOREIGN KEY(id_usuario) REFERENCES usuarios(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contatos_de_emergencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            numero_de_telefone TEXT NOT NULL,
            email TEXT 
        )
    ''')

    conn.commit()
    conn.close()

criar_banco_de_dados()

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha'] 

        senha_criptografada = generate_password_hash(senha)

        conn = sqlite3.connect('alertas.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO usuarios (email, senha) VALUES (?, ?)', (email, senha_criptografada))
            conn.commit()
            return redirect(url_for('index')) 
        except sqlite3.IntegrityError:
            return "Email já existe. Por favor, tente um diferente."
        finally:
            conn.close()

    return render_template('cadastro.html') 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha'] 

        conn = sqlite3.connect('alertas.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = ?', (email,))
        usuario = cursor.fetchone()
        conn.close()

        if usuario and check_password_hash(usuario[2], senha):
            session['id_usuario'] = usuario[0]
            return redirect(url_for('index'))
        else:
            return "Email ou senha inválidos. Por favor, tente novamente."

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('id_usuario', None)  
    return redirect(url_for('index'))

@app.route('/adicionar_alerta', methods=['GET', 'POST'])
def adicionar_alerta():
    if 'id_usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        id_usuario = session['id_usuario']
        local = request.form['local']
        tipo_de_perigo = request.form['tipo_de_perigo']
        nivel_de_alerta = request.form['nivel_de_alerta']
        url_foto_video = request.form.get('url_foto_video') 
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        conn = sqlite3.connect('alertas.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alertas (id_usuario, local, tipo_de_perigo, nivel_de_alerta, url_foto_video, latitude, longitude) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (id_usuario, local, tipo_de_perigo, nivel_de_alerta, url_foto_video, latitude, longitude))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    return render_template('adicionar_alerta.html')

@app.route('/obter_alertas')
def obter_alertas():
    conn = sqlite3.connect('alertas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM alertas')
    alertas = cursor.fetchall()
    conn.close()

    dados_dos_alertas = []
    for alerta in alertas:
        dados_do_alerta = {
            'id': alerta[0],
            'id_usuario': alerta[1],
            'local': alerta[2],
            'tipo_de_perigo': alerta[3],
            'nivel_de_alerta': alerta[4],
            'horario': alerta[5],
            'url_foto_video': alerta[6],
            'latitude': alerta[7],
            'longitude': alerta[8]
        }
        dados_dos_alertas.append(dados_do_alerta)

    return jsonify(dados_dos_alertas)

@app.route('/obter_url_de_upload', methods=['POST'])
def obter_url_de_upload():
    if 'id_usuario' not in session:
        return jsonify({'erro': 'Não autorizado'}), 401

    dados = request.get_json()
    nome_do_arquivo = dados['nome_do_arquivo'] 
    nome_do_bucket = 'projetoenchentes' 

    try:
        resposta = cliente_s3.generate_presigned_url(
            'put_object',
            Params={'Bucket': nome_do_bucket, 'Key': nome_do_arquivo},
            ExpiresIn=3600 
        )
        return jsonify({'url': resposta})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    
@app.route('/apagar_alerta/<int:id_alerta>')
def apagar_alerta(id_alerta):
    if 'id_usuario' not in session:
        return redirect(url_for('login'))

    # Verifica se o usuário atual é o administrador
    if session.get('email_usuario') != 'gustavusousa36@gmail.com':
        return "Você não está autorizado a apagar alertas."

    conn = sqlite3.connect('alertas.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM alertas WHERE id = ?', (id_alerta,))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/adicionar_contato_de_emergencia', methods=['GET', 'POST'])
def adicionar_contato_de_emergencia():
    if 'id_usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        numero_de_telefone = request.form['numero_de_telefone']
        email = request.form.get('email')

        conn = sqlite3.connect('alertas.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO contatos_de_emergencia (nome, numero_de_telefone, email) 
            VALUES (?, ?, ?)
        ''', (nome, numero_de_telefone, email))
        conn.commit()
        conn.close()

        return redirect(url_for('informacoes_de_emergencia')) 

    return render_template('adicionar_contato_de_emergencia.html')

@app.route('/informacoes_de_emergencia')
def informacoes_de_emergencia():
    conn = sqlite3.connect('alertas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM contatos_de_emergencia')
    contatos_de_emergencia = cursor.fetchall()
    conn.close()

    return render_template('informacoes_de_emergencia.html', contatos_de_emergencia=contatos_de_emergencia)

@app.route('/')
def index():
    if 'id_usuario' in session:
        conn = sqlite3.connect('alertas.db')
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM usuarios WHERE id = ?', (session['id_usuario'],))
        email_usuario = cursor.fetchone()
        conn.close()
    else:
        email_usuario = None

    conn = sqlite3.connect('alertas.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM alertas')
    alertas = cursor.fetchall()

    cursor.execute('SELECT * FROM contatos_de_emergencia')
    contatos_de_emergencia = cursor.fetchall()

    conn.close()

    return render_template('index.html', 
                           email_usuario=email_usuario, 
                           alertas=alertas, 
                           contatos_de_emergencia=contatos_de_emergencia)

if __name__ == '__main__':
    app.run(debug=True)