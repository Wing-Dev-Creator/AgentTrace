import os
import asyncio
import agenttrace
from openai import AsyncOpenAI

# 1. Enable auto-instrumentation
agenttrace.instrument()

# Mock key
os.environ["OPENAI_API_KEY"] = "sk-dummy-key"

async def main():
    client = AsyncOpenAI()
    
    print("Starting async trace...")
    with agenttrace.trace("async_demo") as t:
        try:
            print("Calling Async OpenAI (non-stream)...")
            # This call will fail with 401
            await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Async hello"}]
            )
        except Exception as e:
            print(f"Caught expected error: {e}")

        try:
            print("\nCalling Async OpenAI (stream)...")
            stream = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Async stream"}],
                stream=True
            )
            async for chunk in stream:
                print(chunk.choices[0].delta.content or "", end="")
        except Exception as e:
            print(f"Caught expected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

