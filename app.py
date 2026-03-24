import os
import json
import sqlite3
import redis
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Redis Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Initialize Redis connection
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )
except Exception as e:
    redis_client = None
    print(f"Failed to initialize Redis client: {str(e)}")

# SQLite Configuration
DB_FILE = 'app.db'

def init_db():
    """Initializes the SQLite database with the users table and sample data."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE
            )
        ''')
        
        # Insert sample users if table is empty
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            sample_users = [
                ('Alice Smith', 'alice@example.com'),
                ('Bob Jones', 'bob@example.com'),
                ('Charlie Brown', 'charlie@example.com')
            ]
            cursor.executemany('INSERT INTO users (name, email) VALUES (?, ?)', sample_users)
            conn.commit()
            
        conn.close()
    except Exception as e:
        print(f"Database initialization failed: {str(e)}")

# Initialize DB when the app starts
init_db()

def get_db_connection():
    """Returns a connection to the SQLite database with dict-like row access."""
    conn = sqlite3.connect(DB_FILE)
    # This row_factory allows accessing columns by name (e.g., row['name'])
    conn.row_factory = sqlite3.Row
    return conn

def check_redis_connection():
    """Check if Redis is running and reachable."""
    if not redis_client:
        return False
    try:
        return redis_client.ping()
    except Exception:
        return False

# ----------------- #
# Health Routes     #
# ----------------- #

@app.route('/')
def index():
    """Render the main frontend interface instead of JSON."""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Detailed health check for Redis and SQLite connections."""
    redis_connected = check_redis_connection()
    
    db_connected = True
    try:
        conn = get_db_connection()
        conn.execute('SELECT 1').fetchone()
        conn.close()
    except Exception:
        db_connected = False
        
    status = "healthy" if redis_connected and db_connected else "degraded"
    status_code = 200 if status == "healthy" else 503
    
    return jsonify({
        "status": status,
        "redis_status": "connected" if redis_connected else "disconnected",
        "database_status": "connected" if db_connected else "disconnected"
    }), status_code

@app.route('/redis-test')
def get_redis_test():
    """Checks the Redis connection specifically."""
    if check_redis_connection():
        return jsonify({
            "success": True,
            "message": "Successfully connected to Redis"
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": "Failed to connect to Redis. Please ensure the Redis server is running."
        }), 503

# ----------------- #
# Main Data Routes  #
# ----------------- #

@app.route('/user', methods=['POST'])
def create_or_update_user():
    """Create a new user or update an existing one, caching immediately."""
    data = request.get_json()
    if not data or not data.get('name') or not data.get('email'):
        return jsonify({"error": "Name and email are required"}), 400
        
    name = data['name'].strip()
    email = data['email'].strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user with this email already exists
        existing_user = cursor.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        
        if existing_user:
            user_id = existing_user['id']
            cursor.execute('UPDATE users SET name = ? WHERE id = ?', (name, user_id))
            message = "User updated successfully"
        else:
            cursor.execute('INSERT INTO users (name, email) VALUES (?, ?)', (name, email))
            user_id = cursor.lastrowid
            message = "User created successfully"
            
        conn.commit()
        
        # Get the full updated row
        user_row = cursor.execute('SELECT id, name, email FROM users WHERE id = ?', (user_id,)).fetchone()
        user_dict = dict(user_row)
        conn.close()
        
        # Proactively update Redis cache (Write-Through caching style)
        cache_status = "skipped (Redis unavailable)"
        if check_redis_connection():
            try:
                cache_key = f"user:{user_id}"
                redis_client.set(cache_key, json.dumps(user_dict))
                cache_status = "synchronized"
            except Exception as e:
                cache_status = f"failed ({str(e)})"
                
        return jsonify({
            "success": True,
            "message": message,
            "user": user_dict,
            "redis_cache": cache_status
        }), 201
        
    except sqlite3.IntegrityError:
        return jsonify({"error": "A database integrity error occurred"}), 400
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/user/<int:user_id>')
def get_user(user_id):
    """
    Main user route implementing the cache-aside pattern.
    Supports ?refresh=true query parameter to force fetching from DB.
    """
    cache_key = f"user:{user_id}"
    # Check if the user wants to forcefully bypass Redis
    force_refresh = request.args.get('refresh', '').lower() == 'true'
    
    # --- STEP 1: Check Redis Cache (if not refreshing) ---
    if not force_refresh and check_redis_connection():
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data is not None:
                # Cache HIT
                return jsonify({
                    "user": json.loads(cached_data),
                    "source": "redis",
                    "cache_hit": True,
                    "fetched_from_db": False
                }), 200
        except Exception as e:
            # If Redis read fails, gracefully fallback to DB without crashing
            print(f"Redis read error: {e}")

    # --- STEP 2: Fetch from SQLite Database (Cache MISS or forced refresh) ---
    try:
        conn = get_db_connection()
        user_row = conn.execute('SELECT id, name, email FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        
        if user_row is None:
            return jsonify({
                "error": "User not found"
            }), 404
            
        # Convert sqlite3.Row to standard dictionary
        user_dict = dict(user_row)
        
        # --- STEP 3: Save to Redis Cache ---
        cache_refreshed = False
        if check_redis_connection():
            try:
                redis_client.set(cache_key, json.dumps(user_dict))
                cache_refreshed = True
            except Exception as e:
                print(f"Redis write error: {e}")
                
        # Build the final response
        response = {
            "user": user_dict,
            "source": "database",
            "cache_hit": False,
            "fetched_from_db": True
        }
        
        # Optional field for observing the force refresh behavior
        if force_refresh:
            response["cache_refreshed"] = cache_refreshed
            
        return jsonify(response), 200
        
    except Exception as e:
        # Handle SQLite extraction errors
        return jsonify({
            "error": f"Database error: {str(e)}"
        }), 500

# ----------------- #
# Cache Management  #
# ----------------- #

@app.route('/clear-cache/<int:user_id>')
def clear_cache(user_id):
    """Delete a specific user's data from Redis."""
    if not check_redis_connection():
        return jsonify({
            "success": False,
            "error": "Redis connection error, unable to clear cache"
        }), 503
        
    cache_key = f"user:{user_id}"
    try:
        deleted_count = redis_client.delete(cache_key)
        
        if deleted_count > 0:
            return jsonify({"success": True, "message": f"Cache cleared successfully for user {user_id}"}), 200
        else:
            # Key wasn't inside Redis
            return jsonify({"success": True, "message": f"Cache was already empty for user {user_id}"}), 200
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/clear-all-cache')
def clear_all_cache():
    """Delete ALL user keys from Redis."""
    if not check_redis_connection():
        return jsonify({
            "success": False,
            "error": "Redis connection error, unable to clear cache"
        }), 503
        
    try:
        # Use SCAN or KEYS to find any 'user:*' strings
        keys_to_delete = redis_client.keys("user:*")
        
        if keys_to_delete:
            # redis_client.delete accepts multiple keys if destructured
            deleted_count = redis_client.delete(*keys_to_delete)
        else:
            deleted_count = 0
            
        return jsonify({
            "success": True,
            "message": f"All user cache cleared",
            "keys_deleted": deleted_count
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Run the Flask development server on all interfaces
    app.run(host='0.0.0.0', port=5000, debug=True)
