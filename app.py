from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import openai
import os
import re
import fitz  # PyMuPDF
from docx import Document

app = Flask(__name__)

# Set your OpenAI API key here
openai.api_key = ''

# Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://chatbotuser:chatbotpass@localhost:5433/chatbotdb'
app.config['SECRET_KEY'] = ''

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Use a valid schema (must exist in your PostgreSQL DB)
SCHEMA_NAME = 'chatbot_schema'

# Models
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    __table_args__ = {'schema': SCHEMA_NAME}
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)

class Chat(db.Model):
    __tablename__ = 'chat'
    __table_args__ = {'schema': SCHEMA_NAME}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA_NAME}.user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)

# Flask-Login loader (SQLAlchemy 2.x compatible)
@login_manager.user_loader
def load_user(user_id):
    with app.app_context():
        return db.session.get(User, int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
            email = request.form['email']
            first_name = request.form['first_name']
            last_name = request.form['last_name']

            if not re.match(r"^[A-Za-z0-9]+$", username):
                flash("Username must be alphanumeric.")
                return redirect(url_for('register'))

            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                flash("Invalid email address.")
                return redirect(url_for('register'))

            existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
            if existing_user:
                flash("Username or email already taken.")
                return redirect(url_for('register'))

            user = User(username=username, email=email, password=password,
                        first_name=first_name, last_name=last_name)
            db.session.add(user)
            db.session.commit()

            flash("Registration successful! Please log in.")
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred during registration: {str(e)}")
            return redirect(url_for('register'))

        finally:
            db.session.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()

            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('chat'))
            else:
                flash("Invalid username or password.")
                return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred during login: {str(e)}")
            return redirect(url_for('login'))

        finally:
            db.session.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('thank_you'))

@app.route('/chat')
@login_required
def chat():
    history = Chat.query.filter_by(user_id=current_user.id).all()
    full_name = f"{current_user.first_name} {current_user.last_name}"
    email = current_user.email
    return render_template('chat.html', history=history, full_name=full_name, email=email)

@app.route('/ask', methods=['POST'])
@login_required
def ask():
    data = request.get_json()
    question = data.get('question')
    uploaded_content = session.get('uploaded_file_content', '')
    if question:
        response = openai.chat.completions.create(
            model= "gpt-4", #"gpt-3.5-turbo",
            messages=[{"role": "user", "content": question}],
            max_tokens=150,
            temperature=0.7
        )
        answer = response.choices[0].message.content.strip()
        answer = beautify_answer(answer)

        chat_entry = Chat(user_id=current_user.id, message=question, response=answer)
        db.session.add(chat_entry)
        db.session.commit()

        return jsonify({'answer': answer})
    return jsonify({'error': 'No question provided'}), 400

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    filename = file.filename.lower()

    try:
        if filename.endswith('.txt'):
            content = file.read().decode('utf-8')
        
        elif filename.endswith('.pdf'):
            doc = fitz.open(stream=file.read(), filetype="pdf")
            content = "\n".join(page.get_text() for page in doc)

        elif filename.endswith('.docx'):
            doc = Document(file)
            content = "\n".join([para.text for para in doc.paragraphs])

        else:
            return jsonify({'error': 'Unsupported file format'}), 400

        session['uploaded_file_content'] = content
        return jsonify({'message': 'File uploaded successfully', 'content': content})

    except Exception as e:
        return jsonify({'error': f'File processing failed: {str(e)}'}), 400


@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')  # Ensure this template exists

@app.route('/voice-to-text', methods=['POST'])
@login_required
def voice_to_text():
    try:
        transcript = request.get_json().get('transcript')
        if not transcript:
            return jsonify({'error': 'No transcript provided'}), 400
        return jsonify({'question': transcript})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def beautify_answer(answer):
    answer = answer.strip()
    answer = answer.replace('\n', '<br>')
    return answer

# Run App
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
