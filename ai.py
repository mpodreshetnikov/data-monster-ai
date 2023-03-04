import openai

def set_openai_api_key(api_key):
    openai.api_key = api_key

def get_ai_response(prompt):
    response = openai.Completion.create(
        model="code-davinci-002",
        prompt=prompt,
        temperature=0,
        max_tokens=1000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=["#", ";"]
    )
    return response.choices[0].text

def generate_db_request(prompt):
    ai_response = get_ai_response(prompt)
    return f"SELECT {ai_response}"