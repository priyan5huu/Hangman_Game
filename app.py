from flask import Flask, render_template, jsonify, request
import random
import os
import string

app = Flask(__name__, template_folder='.')

# Load words from file
try:
    with open('words.txt', 'r') as f:
        WORDS = [word.strip().upper() for word in f.readlines() if word.strip()]
except FileNotFoundError:
    # Fallback list if file is missing
    WORDS = ["PYTHON", "FLASK", "DEVELOPER", "HANGMAN", "CODING"]

# Store game state in memory (Note: In a real production app, use a database or Redis)
# Structure: { session_id: { 'word': 'XYZ', 'guessed': [], 'chances': 7 } }
games = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_game():
    # Generate a short, memorable 6-character room code
    alphabet = string.ascii_uppercase + string.digits
    session_id = ''.join(random.choices(alphabet, k=6))
    
    data = request.get_json(silent=True) or {}
    custom_word = data.get('custom_word')
    
    if custom_word and custom_word.strip():
        word = custom_word.strip().upper()
        # Basic validation: ensure it contains only letters
        if not word.isalpha():
             return jsonify({'error': 'Word must only contain letters'}), 400
    else:
        word = random.choice(WORDS)

    games[session_id] = {
        'word': word,
        'guessed': [],
        'chances': 7,
        'game_over': False,
        'won': False
    }
    display_word = ['_' for _ in word]
    return jsonify({
        'session_id': session_id,
        'word_length': len(word),
        'display_word': display_word,
        'chances': 7,
        'guessed': [],
        'game_over': False,
        'won': False
    })

@app.route('/api/guess', methods=['POST'])
def guess_letter():
    data = request.json
    session_id = data.get('session_id')
    letter = data.get('letter').upper()
    
    if session_id not in games:
        return jsonify({'error': 'Invalid session'}), 400
    
    game = games[session_id]
    
    if game['game_over']:
        return jsonify({'error': 'Game is over', 'word': game['word']})

    if letter in game['guessed']:
        return jsonify({'message': 'Already guessed', 'status': 'repeat'})

    game['guessed'].append(letter)
    
    if letter not in game['word']:
        game['chances'] -= 1
    
    # Check win/loss condition
    word_completed = all(l in game['guessed'] for l in game['word'])
    if word_completed:
        game['game_over'] = True
        game['won'] = True
    elif game['chances'] <= 0:
        game['game_over'] = True
        game['won'] = False

    # Return the current state of the word (e.g., "_ A _ _")
    display_word = [l if l in game['guessed'] else '_' for l in game['word']]
    
    return jsonify({
        'display_word': display_word,
        'chances': game['chances'],
        'game_over': game['game_over'],
        'won': game['won'],
        'correct_guess': letter in game['word'],
        'secret_word': game['word'] if game['game_over'] else None
    })

@app.route('/api/state', methods=['GET'])
def get_game_state():
    session_id = request.args.get('session_id')
    
    if not session_id or session_id not in games:
        return jsonify({'error': 'Invalid session'}), 400
        
    game = games[session_id]
    
    # Return the current state of the word
    display_word = [l if l in game['guessed'] else '_' for l in game['word']]
    
    return jsonify({
        'display_word': display_word,
        'chances': game['chances'],
        'game_over': game['game_over'],
        'won': game['won'],
        'guessed': game['guessed'],
        'secret_word': game['word'] if game['game_over'] else None
    })

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Please ensure you have flask installed: pip install flask")
    app.run(debug=True, port=5000)