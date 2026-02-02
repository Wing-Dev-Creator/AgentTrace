import os
import agenttrace
from openai import OpenAI

# 1. Enable auto-instrumentation
agenttrace.instrument()

# Mock OpenAI API Key for demo (the real call will fail without it, but the instrument hooks should run)
# In a real scenario, you'd set OPENAI_API_KEY env var
os.environ["OPENAI_API_KEY"] = "sk-dummy-key"

def main():
    client = OpenAI()
    
    # 2. Start tracing scope
    print("Starting trace...")
    with agenttrace.trace("auto_instrument_demo") as t:
        t.user_input("Tell me a joke")
        
        try:
            # 3. Call OpenAI (automatically captured)
            print("Calling OpenAI...")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Tell me a joke"}]
            )
            print(response.choices[0].message.content)
        except Exception as e:
            print(f"Expected error (no valid key): {e}")

if __name__ == "__main__":
    main()
