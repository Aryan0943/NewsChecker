
import os

from dotenv import load_dotenv


# Load environment variables from backend/.env
load_dotenv()


NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"
