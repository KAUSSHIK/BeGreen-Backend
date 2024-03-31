from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
import os
from dotenv import load_dotenv
from openai import OpenAI

app = Flask(__name__)
CORS(app)
app.secret_key = 'begreensecret'

load_dotenv()

app.config['MYSQL_HOST'] = os.getenv('DB_HOST')
app.config['MYSQL_USER'] = os.getenv('DB_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('DB_NAME')

mysql = MySQL(app)

# Load the OpenAI API Key
client = OpenAI(api_key=os.getenv('OPEN_AI_API_KEY'))

# Open the file to get the fine-tuned model ID
with open("fine_tuned_model_id.txt", "r") as file:
    fine_tuned_model_id = file.read().strip()


# Check if we can connect to the database
@app.route('/api/check', methods=['GET'])
def check():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM user")
    res = cur.fetchall()
    return jsonify(res)

# Get a user's friends
@app.route('/api/friends/<user_id>')
def get_friends(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT u.user_id, u.name, u.profile_picture
        FROM user u
        INNER JOIN friends f ON (u.user_id = f.friend_id OR u.user_id = f.user_id)
        WHERE (f.user_id = %s OR f.friend_id = %s) AND u.user_id != %s
    """, (user_id, user_id, user_id))
    friends = cursor.fetchall()
    cursor.close()

    if not friends:
        return jsonify({'friends': []})
    
    friends_data = []
    for friend in friends:
        friends_data.append({
            'user_id': friend[0],
            'name': friend[1],
            'profile_picture': friend[2]
        })

    return jsonify({'friends': friends_data})

# Add a friend
@app.route('/api/friends/add/<user_id>/<friend_id>', methods=['POST'])
def add_friend(user_id, friend_id):
    cursor = mysql.connection.cursor()

    # Check if friendship already exists (friendship is bidirectional)
    cursor.execute("""
        SELECT * FROM friends
        WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)
    """, (user_id, friend_id, friend_id, user_id))
    friendship = cursor.fetchone()
    if friendship:
        return jsonify({'message': 'failure'})

    # If not, add the friendship
    cursor.execute("""
        INSERT INTO friends (user_id, friend_id)
        VALUES (%s, %s)
    """, (user_id, friend_id))
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'success'})

# Register a new user
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    user_id = data['user_id']
    name = data['name']
    email = data['email']
    password = data['password']
    profile_picture = None
    #check if profile picture is provided
    if 'profile_picture' in data and data['profile_picture']:
        profile_picture = data['profile_picture']

    cursor = mysql.connection.cursor()

    # Check if user_id already exists
    cursor.execute("""
        SELECT * FROM user WHERE user_id = %s
    """, (user_id,))
    existing_user = cursor.fetchone()
    if existing_user:
        return jsonify({'message': 'user_id already exists'})

    if profile_picture:
        cursor.execute("""
            INSERT INTO user (user_id, name, email, password, profile_picture)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, name, email, password, profile_picture))
    else:
        cursor.execute("""
            INSERT INTO user (user_id, name, email, password)
            VALUES (%s, %s, %s, %s)
        """, (user_id, name, email, password))
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'success'})


# Login a user
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user_id = data['user_id']
    password = data['password']
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT * FROM user WHERE user_id = %s
    """, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    
    if user:
        stored_password = user[4]  # Assuming the password is stored at index 4
        if password == stored_password:
            return jsonify({
                'user_id': user[1],
                'name': user[2],
                'email': user[3],
                'profile_picture': user[6],
                'points': user[5],
                'daily_points': user[7],
                'weekly_points': user[8],
                'message': 'success'
            })
        else:
            return jsonify({'message': 'invalid credentials'})
    else:
        return jsonify({'message': 'not found'})

# Leaderboard for the user: Get the top 3/5/10 users depending on the amount of friends the user has
@app.route('/api/leaderboard/<user_id>', methods=['GET'])
def leaderboard(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM friends WHERE user_id = %s OR friend_id = %s
    """, (user_id, user_id))
    friends_count = cursor.fetchone()[0]

    if friends_count < 3:
        limit = 3
    elif friends_count < 5:
        limit = 5
    else:
        limit = 10

    cursor.execute("""
        SELECT u.user_id, u.name, u.profile_picture, u.points
        FROM user u
        INNER JOIN friends f ON (u.user_id = f.friend_id OR u.user_id = f.user_id)
        WHERE (f.user_id = %s OR f.friend_id = %s) AND u.user_id != %s
        ORDER BY u.points DESC
        LIMIT %s
    """, (user_id, user_id, user_id, limit))
    leaderboard = cursor.fetchall()
    cursor.close()

    if not leaderboard:
        return jsonify({'leaderboard': []})
    
    leaderboard_data = []
    for friends in leaderboard:
        leaderboard_data.append({
            'user_id': friends[0],
            'name': friends[1],
            'profile_picture': friends[2],
            'points': friends[3]
        })

    return jsonify({'leaderboard': leaderboard_data})


# Leaderboard for the user: Get the top 3/5/10 users depending on the amount of friends the user has DAILY_SCORE
@app.route('/api/leaderboard/daily/<user_id>', methods=['GET'])
def leaderboard_daily(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM friends WHERE user_id = %s OR friend_id = %s
    """, (user_id, user_id))
    friends_count = cursor.fetchone()[0]
    if friends_count < 3:
        limit = 3
    elif friends_count < 5:
        limit = 5
    else:
        limit = 10
    cursor.execute("""
        SELECT u.user_id, u.name, u.profile_picture, u.daily_score
        FROM user u
        INNER JOIN friends f ON (u.user_id = f.friend_id OR u.user_id = f.user_id)
        WHERE (f.user_id = %s OR f.friend_id = %s) AND u.user_id != %s
        ORDER BY u.daily_score DESC
        LIMIT %s
    """, (user_id, user_id, user_id, limit))
    leaderboard = cursor.fetchall()
    cursor.close()
    if not leaderboard:
        return jsonify({'leaderboard': []})
    leaderboard_data = []
    for friends in leaderboard:
        leaderboard_data.append({
            'user_id': friends[0],
            'name': friends[1],
            'profile_picture': friends[2],
            'daily_score': friends[3]
        })
    return jsonify({'leaderboard': leaderboard_data})

# Leaderboard for the user: Get the top 3/5/10 users depending on the amount of friends the user has WEEKLY_SCORE
@app.route('/api/leaderboard/weekly/<user_id>', methods=['GET'])
def leaderboard_weekly(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM friends WHERE user_id = %s OR friend_id = %s
    """, (user_id, user_id))
    friends_count = cursor.fetchone()[0]
    if friends_count < 3:
        limit = 3
    elif friends_count < 5:
        limit = 5
    else:
        limit = 10
    cursor.execute("""
        SELECT u.user_id, u.name, u.profile_picture, u.weekly_score
        FROM user u
        INNER JOIN friends f ON (u.user_id = f.friend_id OR u.user_id = f.user_id)
        WHERE (f.user_id = %s OR f.friend_id = %s) AND u.user_id != %s
        ORDER BY u.weekly_score DESC
        LIMIT %s
    """, (user_id, user_id, user_id, limit))
    leaderboard = cursor.fetchall()
    cursor.close()
    if not leaderboard:
        return jsonify({'leaderboard': []})
    leaderboard_data = []
    for friends in leaderboard:
        leaderboard_data.append({
            'user_id': friends[0],
            'name': friends[1],
            'profile_picture': friends[2],
            'weekly_score': friends[3]
        })
    return jsonify({'leaderboard': leaderboard_data})


# Update the user's points
@app.route('/api/update/points/<user_id>/<points>', methods=['POST'])
def update_points(user_id, points):
    points = int(points)
    cursor = mysql.connection.cursor()
    # Check if the user exists:
    cursor.execute("""
        SELECT * FROM user WHERE user_id = %s
    """, (user_id,))
    user = cursor.fetchone()
    if not user:
        return jsonify({'message': 'not found'})
    else:
        cursor.execute("""
            UPDATE user
            SET points = points + %s
            WHERE user_id = %s
        """, (points, user_id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({'message': 'success'})

# Update the user's daily score
@app.route('/api/update/daily_score/<user_id>/<daily_score>', methods=['POST'])
def update_daily_score(user_id, daily_score):
    daily_score = int(daily_score)
    cursor = mysql.connection.cursor()
    # Check if the user exists:
    cursor.execute("""
        SELECT * FROM user WHERE user_id = %s
    """, (user_id,))
    user = cursor.fetchone()
    if not user:
        return jsonify({'message': 'not found'})
    else:
        cursor.execute("""
        UPDATE user
        SET daily_score = daily_score + %s, points = points + %s
        WHERE user_id = %s
    """, (daily_score, daily_score, user_id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({'message': 'success'})

# Update the user's weekly score
@app.route('/api/update/weekly_score/<user_id>/<weekly_score>', methods=['POST'])
def update_weekly_score(user_id, weekly_score):
    weekly_score = int(weekly_score)
    cursor = mysql.connection.cursor()
    # Check if the user exists:
    cursor.execute("""
        SELECT * FROM user WHERE user_id = %s
    """, (user_id,))
    user = cursor.fetchone()
    if not user:
        return jsonify({'message': 'not found'})
    else:
        cursor.execute("""
            UPDATE user
            SET weekly_score = weekly_score + %s, points = points + %s
            WHERE user_id = %s
        """, (weekly_score, weekly_score, user_id))
        mysql.connection.commit()
        cursor.close()

        return jsonify({'message': 'success'})


# ALL GET REQUESTS
# Get the user's points
@app.route('/api/get/points/<user_id>', methods=['GET'])
def get_points(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT points FROM user WHERE user_id = %s
    """, (user_id,))
    points = cursor.fetchone()
    cursor.close()

    if not points:
        return jsonify({'points': 0})
    
    return jsonify({'points': points[0]})

# Get the user's daily score
@app.route('/api/get/daily_score/<user_id>', methods=['GET'])
def get_daily_score(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT daily_score FROM user WHERE user_id = %s
    """, (user_id,))
    daily_score = cursor.fetchone()
    cursor.close()

    if not daily_score:
        return jsonify({'daily_score': 0})
    
    return jsonify({'daily_score': daily_score[0]})

# Get the user's weekly score
@app.route('/api/get/weekly_score/<user_id>', methods=['GET'])
def get_weekly_score(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT weekly_score FROM user WHERE user_id = %s
    """, (user_id,))
    weekly_score = cursor.fetchone()
    cursor.close()

    if not weekly_score:
        return jsonify({'weekly_score': 0})
    
    return jsonify({'weekly_score': weekly_score[0]})

# Get the user's profile picture
@app.route('/api/get/profile_picture/<user_id>', methods=['GET'])
def get_profile_picture(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT profile_picture FROM user WHERE user_id = %s
    """, (user_id,))
    profile_picture = cursor.fetchone()
    cursor.close()

    if not profile_picture:
        return jsonify({'profile_picture': 'not found'})

    return jsonify({'profile_picture': profile_picture[0]})

# Get the user's name
@app.route('/api/get/name/<user_id>', methods=['GET'])
def get_name(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT name FROM user WHERE user_id = %s
    """, (user_id,))
    name = cursor.fetchone()
    cursor.close()

    if not name:
        return jsonify({'name': 'not found'})

    return jsonify({'name': name[0]})

# Get the user's email
@app.route('/api/get/email/<user_id>', methods=['GET'])
def get_email(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT email FROM user WHERE user_id = %s
    """, (user_id,))
    email = cursor.fetchone()
    cursor.close()

    if not email:
        return jsonify({'email': 'not found'})

    return jsonify({'email': email[0]})

# Get the user's friends count
@app.route('/api/get/friends_count/<user_id>', methods=['GET'])
def get_friends_count(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM friends WHERE user_id = %s OR friend_id = %s
    """, (user_id, user_id))
    friends_count = cursor.fetchone()
    cursor.close()

    if not friends_count:
        return jsonify({'friends_count': 0})

    return jsonify({'friends_count': friends_count[0]})


# SETTERS
# Set the user's profile picture
@app.route('/api/set/profile_picture/<user_id>/<profile_picture>', methods=['POST'])
def set_profile_picture(user_id, profile_picture):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE user
        SET profile_picture = %s
        WHERE user_id = %s
    """, (profile_picture, user_id))
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'success'})


# Delete a user
@app.route('/api/delete/user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    cursor = mysql.connection.cursor()

    try:
        # Delete the user's friendships from the friends table
        cursor.execute("""
            DELETE FROM friends
            WHERE user_id = %s OR friend_id = %s
        """, (user_id, user_id))

        # Delete the user from the user table
        cursor.execute("""
            DELETE FROM user
            WHERE user_id = %s
        """, (user_id,))

        mysql.connection.commit()
        return jsonify({'message': 'success'})

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': 'error', 'error': str(e)}), 500

    finally:
        cursor.close()


# IF ONE OF THSE IS THROWING 503 - CHECK IF USER_ID EXISTS IN THE DATABASE FIRST, THEN PROCEED
# Add a badge/assign a badge to a user
@app.route('/api/badges/add/<badge_id>/<user_id>', methods=['POST'])
def add_badge(badge_id, user_id):
    cursor = mysql.connection.cursor()

    # Check if the badge already exists
    cursor.execute("""
        SELECT * FROM badge WHERE user_id = %s AND badge_id = %s
    """, (user_id, badge_id))
    existing_badge = cursor.fetchone()
    if existing_badge:
        return jsonify({'message': 'already exists'})

    # If not, add the badge
    cursor.execute("""
        INSERT INTO badge (user_id, badge_id)
        VALUES (%s, %s)
    """, (user_id, badge_id))
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'success'})

# Get the user's badges
@app.route('/api/badges/<user_id>', methods=['GET'])
def get_badges(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT b.badge_id
        FROM badge b
        INNER JOIN user u ON u.user_id = b.user_id
        WHERE u.user_id = %s
    """, (user_id,))
    badges = cursor.fetchall()
    cursor.close()

    if not badges:
        return jsonify({'badges': []})
    
    badges_data = []
    for badge in badges:
        badges_data.append({
            'badge_id': badge[0],
        })

    return jsonify({'badges': badges_data})

# Delete the user's badge
@app.route('/api/badges/delete/<badge_id>/<user_id>', methods=['DELETE'])
def delete_badge(badge_id, user_id):
    cursor = mysql.connection.cursor()

    try:
        # Delete the badge from the badge table
        cursor.execute("""
            DELETE FROM badge
            WHERE user_id = %s AND badge_id = %s
        """, (user_id, badge_id))

        mysql.connection.commit()
        return jsonify({'message': 'success'})

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'message': 'error', 'error': str(e)}), 500

    finally:
        cursor.close()

# Set the all users' daily score to zero upon request
@app.route('/api/reset/daily_score', methods=['POST'])
def reset_daily_score():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE user
        SET daily_score = 0
    """)
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'success'})

# Set the all users' weekly score to zero upon request
@app.route('/api/reset/weekly_score', methods=['POST'])
def reset_weekly_score():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE user
        SET weekly_score = 0
    """)
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'success'})


# Predict the sustainability points for an activity using OPEN AI
@app.route('/api/predict-points', methods=['POST'])
def predict_points():
    activity = request.json['activity']

    # Use the fine-tuned model for predictions
    response = client.completions.create(
        model=fine_tuned_model_id,
        prompt=f"Predict the sustainability points for the following activity: {activity}",
        max_tokens=17,
        n=1,
        stop=None,
        temperature=0.7,
    )
    predicted_points = response.choices[0].text.strip()

    return jsonify({'predicted_points': predicted_points})




# Main Function
if __name__ == '__main__':
    app.run(debug=True)