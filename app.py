from flask import Flask, render_template, jsonify, request
import random
import string
import time
import threading

app = Flask(__name__, template_folder='.')

# Load words from file
try:
    with open('words.txt', 'r') as f:
        WORDS = [word.strip().upper() for word in f.readlines() if word.strip()]
except FileNotFoundError:
    # Fallback list if file is missing
    WORDS = ["PYTHON", "FLASK", "DEVELOPER", "HANGMAN", "CODING"]

# Game Configuration
MAX_GAMES = 1000  # Maximum number of active games to prevent memory exhaustion
GAME_TTL = 3600   # Time to live for a game in seconds (1 hour)

# Store game state in memory
# Structure: { session_id: { 'word': 'XYZ', 'guessed': [], 'chances': 7, 'last_activity': timestamp } }
games = {}
game_lock = threading.Lock()

def cleanup_games():
    """Remove games that are older than GAME_TTL or if limit is reached."""
    current_time = time.time()
    to_remove = []
    
    # Identify old games
    for session_id, game in games.items():
        if current_time - game['last_activity'] > GAME_TTL:
            to_remove.append(session_id)
            
    # Remove old games
    for session_id in to_remove:
        del games[session_id]
        
    # If still over limit, remove oldest games
    if len(games) > MAX_GAMES:
        # Sort by activity time
        sorted_games = sorted(games.items(), key=lambda x: x[1]['last_activity'])
        # Remove oldest to get back to 90% capacity
        excess = len(games) - int(MAX_GAMES * 0.9)
        for i in range(excess):
            del games[sorted_games[i][0]]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_game():
    with game_lock:
        # Run cleanup occasionally or if full
        if len(games) >= MAX_GAMES:
            cleanup_games()
            
        # Generate a unique 6-character room code
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(10): # Try 10 times to find a unique ID
            session_id = ''.join(random.choices(alphabet, k=6))
            if session_id not in games:
                break
        else:
            return jsonify({'error': 'Server busy, please try again later'}), 503
        
        data = request.get_json(silent=True) or {}
        custom_word = data.get('custom_word')
        
        if custom_word:
            # Strict validation for custom words
            clean_word = custom_word.strip().upper()
            if not clean_word.isalpha():
                 return jsonify({'error': 'Word must only contain letters'}), 400
            if len(clean_word) < 3 or len(clean_word) > 20:
                 return jsonify({'error': 'Word must be between 3 and 20 characters'}), 400
            word = clean_word
        else:
            word = random.choice(WORDS)
    
        games[session_id] = {
            'word': word,
            'guessed': [],
            'chances': 7,
            'game_over': False,
            'won': False,
            'last_activity': time.time()
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
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
        
    session_id = data.get('session_id')
    letter = data.get('letter')
    
    # Input Validation
    if not session_id or not isinstance(session_id, str):
        return jsonify({'error': 'Invalid session ID'}), 400
    
    if not letter or not isinstance(letter, str) or len(letter) != 1 or not letter.isalpha():
        return jsonify({'error': 'Invalid guess. Must be a single letter.'}), 400
        
    letter = letter.upper()
    
    with game_lock:
        if session_id not in games:
            return jsonify({'error': 'Invalid session or game expired'}), 404
        
        game = games[session_id]
        game['last_activity'] = time.time() # Update activity
        
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
    
        # Return the current state of the word
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
    
    with game_lock:
        if not session_id or session_id not in games:
            return jsonify({'error': 'Invalid session or game expired'}), 404
            
        game = games[session_id]
        game['last_activity'] = time.time() # Update activity
        
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