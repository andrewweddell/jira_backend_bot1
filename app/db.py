from pymongo import MongoClient, errors

try:
    client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
    db = client.sprintReportBot
    sprints = db.sprints
    client.admin.command('ping')
    print("MongoDB connected successfully")
except errors.ServerSelectionTimeoutError as err:
    print(f"Error connecting to MongoDB: {err}")
    sprints = None