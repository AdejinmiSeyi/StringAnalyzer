from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Any, Dict, Optional
# import requests
import hashlib
import re

app = FastAPI(title = "String Analyzer")

# In-memory storage (simulating a database)
analysis_db: Dict[str, dict] = {}
# string_id = 0

class String_to_analyze(BaseModel):
    text: str

class Item_in_db(BaseModel):
    id: str
    analyzed_str: str
    properties: dict

# Helper function for sha256   # sha256 instance
def sha_encoder(text:str):
    sha256_hash = hashlib.sha256(text.encode('utf-8'))
    sha_id = str(sha256_hash.hexdigest())
    return sha_id 

# palindrome logic
def is_palindrome(text:str):
    return text.lower() == text.lower()[::-1]

# word count logic
def word_count(text:str): 
    return len(text.split())

# unique characters
def unique_chars(text):
    return len(set(text))

# create instance of character frequency
def count_char_frequency_dict(text):
    frequency = {}
    for char in text:
        if char in frequency:
            frequency[char] += 1
        else:
            frequency[char] = 1
    return frequency

# def contains_character(text):
#     for i in text:
#         return i
# existing_data = {}

@app.post("/strings")
def check_string(data:String_to_analyze):
    
    # Get the current time in UTC - ISO 8601 format
    now_utc = datetime.now(timezone.utc)

      
    # Accepts a string and returns string properties
    text = data.text

    string_id = sha_encoder(text)

    analysis_db[string_id] = {
    
    "id": string_id,
    "value" : text,
    "properties": {
    "length": len(text),
    "is_palindrome": is_palindrome(text),
    "unique_characters": unique_chars(text),
    "word_count": word_count(text),
    "sha256_hash": sha_encoder(text),
    "character_frequency_map": count_char_frequency_dict(text)
    },  
    "created at": now_utc
    }

    # Error catchers 409, 400 and 422
    if id in analysis_db:
        raise HTTPException(
            status_code=409,
            detail="String already exists in the system"
        )
    
    if text is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid request body or missing 'value' field"

        )
    
    if type(text) is not str:
        raise HTTPException(
            status_code=422,
            detail="Invalid data type for 'value' (must be string)"
        )
    
    
    return analysis_db[string_id]


  
@app.get("/strings/{string_value}")
async def get_string(string_id:str):
    
     # Get the current time in UTC - ISO 8601 format
    now_utc = datetime.now(timezone.utc)

    
    if string_id in analysis_db:
        return analysis_db[string_id]
    else:
        raise HTTPException(status_code=404, detail="String does not exist in the system")


@app.get("/strings")
async def filter_string(
     is_palindrome: Optional[bool] = None,
     min_length: Optional[int] = None,
     max_length: Optional[int] = None,
     word_count: Optional[int] = None,
     contains_character: Optional[str] = None,
):
    
    if min_length is not None and max_length is not None and min_length > max_length:
        raise HTTPException(
            status_code=400,
            detail=" Invalid query parameter values or types"
        )

    filtered_strings = []
    

    # loop through all items in the database
    for string in analysis_db.values():
        text_length = len(string["value"])


        if (
            (is_palindrome is None or string["properties"]["is_palindrome"] == is_palindrome)
            and (word_count is None or string["properties"]["word_count"] == word_count) 
            and (min_length is None or text_length >= min_length)
            and (max_length is None or text_length <= max_length)
            and (contains_character is None or contains_character in string["value"])
        ):
            filtered_strings.append(string)
    return filtered_strings


def parse_natural_language_query(query: str):
    """
    Parses a natural language query string into filter rules.
    This is a simple rule-based parser for the requested queries.
    """
    if not query:
        return {}
        
    query = query.lower()
    filters = {}

    # Check for specific phrase "single word" and "palindromic strings"
    if "single word palindromic strings" in query:
        filters["word_count"] = 1
        filters["is_palindrome"] = True
    elif "single word" in query:
        filters["word_count"] = 1
        try:
            # Extract number from query, like "longer than 10 characters"
            min_length = int(query.split("longer than ")[1].split(" characters")[0])
            filters["min_length"] = min_length + 1
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot parse query: '{query}'. Please specify a valid length."
            )
    
    # Check for "strings longer than X characters"
    match = re.search(r"longer than (\d+) characters", query)
    if match:
        filters["min_length"] = int(match.group(1)) + 1
        
    # Check for "palindromic strings that contain..."
    if "palindromic strings" in query:
        filters["is_palindrome"] = True

    # Check for "strings containing the letter X"
    match = re.search(r"strings containing the letter ([a-z])", query)
    if match:
        filters["contains_character"] = match.group(1)

    # Check for "contains a vowel"
    if "contains a vowel" in query:
        filters["contains_vowel"] = True
        
    return filters



@app.get("/strings/filter-by-natural-language")
def natural_language_filter(query: str = Query(None, description="Natural language query for filtering")):
    """
    Filters the in-memory database based on a natural language query.
    """
    # If no query is provided, return the full database
    if not query:
        return analysis_db

    # Parse the natural language query into specific filters
    filters = parse_natural_language_query(query)

    # Filter the database based on the parsed filters
    filtered_results = {}
    for key, value in analysis_db.items():
        match = True
        
        # Apply word count filter
        if "word_count" in filters:
            if len(value.split()) != filters["word_count"]:
                match = False
        
        # Apply palindrome filter
        if "is_palindrome" in filters:
            if not is_palindrome(value):
                match = False

        # Apply minimum length filter
        if "min_length" in filters:
            if len(value) < filters["min_length"]:
                match = False

        # Apply contains specific character filter
        if "contains_character" in filters:
            if filters["contains_character"] not in value:
                match = False

        # Apply contains vowel filter
        if "contains_vowel" in filters:
            if not any(vowel in value for vowel in "aeiou"):
                match = False

        if match:
            filtered_results[key] = value

    return filtered_results




@app.delete("/strings/{string_value}")
def delete_string(string:str):
    
    if string in analysis_db:
        del analysis_db[string]
        return
    else:
        raise HTTPException(
            status_code=404,
            detail="String does not exist in the system"
        )
    

    
    


    
'''
      string_props = Props(
      length= len(string),
      is_palindrome = palindrome, 
      unique_characters = unique_chars,
      word_count =  len(words),
      sha256_hash = sha_id,
      character_freqency_map = char_frequency
    )

    # create instance of string analyzer

    analyze_string = Analyze (
      id = sha_id,
      value = string,
      properties = string_props,
      created_at = now_utc
  
    )
    
    return {"analyze_string": data}

    initial frequency logic
def frequency(text:str):
    char_frequency = {}

    # unique characters using set
    unique_chars = set(text.str)
    # no_of

    for char in unique_chars:
        char_frequency[char] = text.count(char)
    return char_frequency
      

    

{
   "id": "sha256_hash_value",
   "value": "string to analyze",
   "properties": {
     "length": 17,
     "is_palindrome": false,
     "unique_characters": 12,
     "word_count": 3,
     "sha256_hash": "abc123...",
     "character_frequency_map": {
       "s": 2,
       "t": 3,
       "r": 2,
       // ... etc
     }
   },
   "created_at": "2025-08-27T10:00:00Z"
 }


class Item(BaseModel):
    name: str
    timestamp: datetime

# Define Properies model
class Props(BaseModel):
    length: int
    is_palindrome: bool
    unique_characters: int
    word_count: int
    sha256_hash: str
    character_freqency_map: str

# Define String Analyzer model
class Analyze(BaseModel):
    id: str
    value: str
    properties: str
    created_at: datetime

data: Any = [
    {
      "length": int,
      "is_palindrome": bool,
      "unique_characters": int,
      "word_count": int,
      "sha256_hash": str,
      "character_freqency_map": str
    }
]

strings = []

'''