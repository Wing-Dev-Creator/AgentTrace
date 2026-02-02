from agenttrace import Tracer

if __name__ == "__main__":
    with Tracer(trace_name="langchain_basic") as t:
        t.user_input("hello")
        t.llm_request({"model": "gpt-4o-mini", "prompt": "hello"})
        t.llm_response({"text": "hi"})
