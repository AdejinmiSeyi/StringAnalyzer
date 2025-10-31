from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Dict, Optional
import hashlib


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


def analyze_string_properties(text: str):
    """
    Analyzes a string and returns a dictionary of its properties.
    The SHA256 hash is used as a unique ID for each string.
    """
    # Get the current time in UTC - ISO 8601 format
    now_utc = datetime.now(timezone.utc)

    # sha_id
    text_id = sha_encoder(text)

    properties = {
        "length": len(text),
        "is_palindrome": is_palindrome(text),
        "unique_characters": unique_chars(text),
        "word_count": word_count(text),
        "sha256_hash": sha_encoder(text),
        "character_frequency_map": count_char_frequency_dict(text)
        # "contains_character": 'a' in text.lower()
        # "contains_vowel_a": 'a' in text.lower(),
        # "contains_char_z": 'z' in text.lower()
        }
    created_at = now_utc    

    return {"string": text, "id": text_id, "properties": properties, "created at": created_at}

@app.post("/strings")
def check_string(payload: String_to_analyze):
    
    text = payload.text
    # Accepts a string and returns string properties
    data = analyze_string_properties(text)

    id = data["id"]

    # analysis_db[string_id]

    # Error catchers 409, 400 and 422
    if id in analysis_db:
        raise HTTPException(
            status_code=409,
            detail="String already exists in the system"
        )
    
    
    if id is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid request body or missing 'value' field"
        )
    
    if not isinstance(id,  str):
        
        raise HTTPException(
            status_code=422,
            detail="Invalid data type for 'value' (must be string)"
        )
    analysis_db[id] = data
    return data


# --------------------------
def parse_natural_language_query(query: str) -> dict:
    query = query.lower()
    filters = {}

    if "palindrome" in query:
        filters["is_palindrome"] = True
    if "single word" in query or "one word" in query:
        filters["word_count"] = 1
    if "contains" in query:
        parts = query.split("contains")
        if len(parts) > 1:
            char = parts[1].strip().split()[0]
            filters["contains_character"] = char

    return filters


    
@app.get("/strings/filter-by-natural-language")
async def filter_by_natural_language(query: str = Query(..., description="Natural language query for filtering strings")):
    filters = parse_natural_language_query(query)
    
    # Error catchers 400
    if not filters:
        raise HTTPException(status_code=400, detail="Invalid or unsupported natural language query.")

    # 422: Conflicting filters (example: word_count=1 and word_count=2)
    if "word_count" in filters and filters["word_count"] < 0:
        raise HTTPException(
            status_code=422,
            detail="Query parsed but resulted in conflicting filters"
        )

    results = list(analysis_db.values())

    if "is_palindrome" in filters:
        results = [s for s in results if s["properties"]["is_palindrome"] == filters["is_palindrome"]]
    if "word_count" in filters:
        results = [s for s in results if s["properties"]["word_count"] == filters["word_count"]]
    if "contains_character" in filters:
        results = [s for s in results if filters["contains_character"] in s["string"]]
    if "min_length" in filters:
        results = [s for s in results if s["properties"]["length"] >= filters["min_length"]]
    if "max_length" in filters:
        results = [s for s in results if s["properties"]["length"] <= filters["max_length"]]

    return results







# ------------------------

@app.get("/strings/{string_value}")
async def get_string(string_value:str):
    
     # Get the current time in UTC - ISO 8601 format
    # now_utc = datetime.now(timezone.utc)

    for data in analysis_db.values():

        if data["string"] == string_value:

            return data
    else:
        raise HTTPException(status_code=404, detail="String does not exist in the system")



@app.get("/strings")
def get_all_strings_with_filters(
    is_palindrome: Optional[bool] = Query(None),
    min_length: Optional[int] = Query(None, ge=0),
    max_length: Optional[int] = Query(None, ge=0),
    word_count: Optional[int] = Query(None, ge=0),
    contains_character: Optional[str] = Query(None, min_length=1, max_length=1)
):
    # Validate query logic
    if min_length is not None and max_length is not None and min_length > max_length:
        raise HTTPException(
            status_code=400,
            detail="min_length cannot be greater than max_length"
        )

    results = list(analysis_db.values())

    if is_palindrome is not None:
        results = [s for s in results if s["properties"]["is_palindrome"] == is_palindrome]
    if min_length is not None:
        results = [s for s in results if s["properties"]["length"] >= min_length]
    if max_length is not None:
        results = [s for s in results if s["properties"]["length"] <= max_length]
    if word_count is not None:
        results = [s for s in results if s["properties"]["word_count"] == word_count]
    if contains_character is not None:
        results = [s for s in results if contains_character.lower() in s["string"].lower()]

    return results


@app.delete("/strings/{string_value}", status_code=204)
def delete_string(string_value:str):
    
    if string_value in analysis_db:
        del analysis_db[string_value]
        return Response(status_code=204)
    else:
        raise HTTPException(
            status_code=404,
            detail="String does not exist in the system"
        )
    

    
