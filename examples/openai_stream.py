import os
import agenttrace
from openai import OpenAI

# 1. Enable auto-instrumentation
agenttrace.instrument()

# Mock key
os.environ["OPENAI_API_KEY"] = "sk-dummy-key"

def main():
    client = OpenAI()
    
    print("Starting trace for streaming...")
    with agenttrace.trace("streaming_demo") as t:
        try:
            print("Calling OpenAI with stream=True...")
            # This call will fail with 401, but we want to see if the hook triggers
            stream = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Write a long poem"}],
                stream=True
            )
            for chunk in stream:
                print(chunk.choices[0].delta.content or "", end="")
        except Exception as e:
            print(f"\nCaught expected error: {e}")

if __name__ == "__main__":
    main()

