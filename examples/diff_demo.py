from agenttrace import Tracer

if __name__ == "__main__":
    with Tracer(trace_name="diff_demo") as t:
        t.user_input("hello")
        # Change: different model and prompt
        t.llm_request({"model": "gpt-4", "prompt": "hello world"})
        t.llm_response({"text": "hi there"})
