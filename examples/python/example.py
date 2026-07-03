from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-your-llm-key")
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Tell me about the latest AI trends. <context>arxiv paper from 2022</context>"}
    ]
)
print(response.choices[0].message.content)