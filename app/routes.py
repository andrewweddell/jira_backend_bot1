import os
import openai
from flask import request, jsonify, current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from .services import fetch_boards, fetch_sprint_data, summarize_data, send_email, convert_objectid
from .db import sprints

openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/fetch-boards', methods=['GET'])
@jwt_required()
def get_boards():
    try:
        boards = fetch_boards()
        return jsonify(boards)
    except requests.RequestException as e:
        print(f"Error fetching boards: {e}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/fetch-sprint', methods=['POST'])
@jwt_required()
def fetch_sprint():
    data = request.json
    board_id = data.get('board_id')
    if not board_id:
        return jsonify({"error": "Board ID is required"}), 400

    identity = get_jwt_identity()
    if sprints is None:
        return jsonify({"error": "Database connection error"}), 500

    try:
        sprint_data = fetch_sprint_data(board_id)
        if sprint_data:
            summarized_data = summarize_data(sprint_data['summary'])
            sprints.insert_one({
                "name": sprint_data['name'],
                "tickets": sprint_data['tickets'],
                "summary": sprint_data['summary'],
                "summary_ai": summarized_data
            })
            send_email(
                subject=f"Sprint Report: {sprint_data['name']}",
                body=summarized_data,
                to='client@example.com'
            )
            return jsonify({
                "sprint": sprint_data,
                "summary_ai": summarized_data
            })
        return jsonify({"error": "No active sprint found"}), 404
    except requests.RequestException as e:
        print(f"Error in fetch_sprint: {e}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/current-sprint', methods=['GET'])
@jwt_required()
def get_current_sprint():
    identity = get_jwt_identity()
    if sprints is None:
        return jsonify({"error": "Database connection error"}), 500
    try:
        current_sprint = sprints.find().sort('date', -1).limit(1)
        sprint_data = list(current_sprint)
        if sprint_data:
            return jsonify(convert_objectid(sprint_data[0]))
        else:
            return jsonify({"error": "No sprint data found"}), 404
    except Exception as e:
        print(f"Error in get_current_sprint: {e}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/list-sprints', methods=['GET'])
@jwt_required()
def list_sprints():
    identity = get_jwt_identity()
    all_sprints = list(sprints.find())
    return jsonify(convert_objectid(all_sprints))

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    if username == 'admin' and password == 'password':
        access_token = create_access_token(identity={'username': username})
        return jsonify(access_token=access_token)
    return jsonify({'msg': 'Invalid credentials'}), 401