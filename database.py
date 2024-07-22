import streamlit as st
from pymongo import MongoClient

# URI = "mongodb+srv://streamlit:UTQcC5RqaIcXOmLO@cluster0.idvjl5f.mongodb.net/streamlit?retryWrites=true&w=majority"
URI = st.secrets["MONGO_URI"]

# Singleton pattern for the database client
class MongoDBClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
            cls._instance.client = MongoClient(URI)
        return cls._instance

# Create a global database client
db_client = MongoDBClient()


# Select the database and collection
db = db_client.client.streamlit
budget_tracking = db.budget_tracking

def insert_period(period, incomes, expenses, comment):
    """Inserts a new document into the collection"""
    data = {"key": period, "incomes": incomes, "expenses": expenses, "comment": comment}
    return budget_tracking.insert_one(data)

def fetch_all_periods():
    """Returns a cursor to all documents in the collection"""
    return budget_tracking.find()

def get_period(period):
    """Retrieves a single document from the collection by key"""
    return budget_tracking.find_one({"key": period})

def update_period(period_key, new_incomes, new_expenses, new_comment):
    """Update an existing period with new data"""
    filter_query = {"key": period_key}
    update_query = {
        "$set": {
            "incomes": new_incomes,
            "expenses": new_expenses,
            "comment": new_comment
        }
    }

    try:
        result = budget_tracking.update_one(filter_query, update_query)

        if result.matched_count > 0 and result.modified_count > 0:
            return "Data updated successfully"
        elif result.matched_count > 0 and result.modified_count == 0:
            return "No changes made to the data"
        else:
            return "No matching document found for update"

    except Exception as err:
        return f"Error updating data: {str(err)}"


