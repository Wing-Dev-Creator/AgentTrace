import sys
from typing import Protocol, Any, Dict
from agenttrace import Tracer
from agenttrace.replayer import Replayer

# --- The Interface (Abstracts I/O) ---
class AgentIO(Protocol):
    def get_user_input(self, prompt: str) -> str: ...
    def call_llm(self, prompt: str) -> str: ...

# --- Implementation 1: Live (Real Execution) ---
class LiveIO:
    def __init__(self, tracer: Tracer):
        self.tracer = tracer

    def get_user_input(self, prompt: str) -> str:
        # In a real app, this might be input()
        # For this demo, we simulate a user typing
        text = "What is the capital of France?"
        print(f"[User] {text}")
        self.tracer.user_input(text)
        return text

    def call_llm(self, prompt: str) -> str:
        self.tracer.llm_request({"prompt": prompt})
        
        # Simulate Network/API latency and result
        print(f"[System] Calling OpenAI with '{prompt}'...")
        result = "Paris" 
        
        self.tracer.llm_response({"text": result})
        return result

# --- Implementation 2: Replay (Deterministic) ---
class ReplayIO:
    def __init__(self, replayer: Replayer):
        self.replayer = replayer

    def get_user_input(self, prompt: str) -> str:
        # Don't ask user, ask trace
        text = self.replayer.consume_input()
        print(f"[Replay] Mocked User Input: {text}")
        return text

    def call_llm(self, prompt: str) -> str:
        # Don't call API, ask trace
        payload = self.replayer.expect_llm(prompt_match=prompt)
        text = payload["text"]
        print(f"[Replay] Mocked LLM Response: {text}")
        return text

# --- The Agent Logic (Unchanged!) ---
def run_agent(io: AgentIO):
    query = io.get_user_input("Ask me anything: ")
    answer = io.call_llm(query)
    print(f"Agent Final Answer: {answer}")

# --- Main Driver ---
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "live"

    if mode == "live":
        print("--- STARTING LIVE RUN ---")
        with Tracer(trace_name="replay_demo") as t:
            io = LiveIO(t)
            run_agent(io)
            print(f"Trace saved to: {t.trace_id}")
            
            # Save ID for replay
            with open(".last_trace", "w") as f:
                f.write(t.trace_id)

    elif mode == "replay":
        try:
            with open(".last_trace", "r") as f:
                trace_id = f.read().strip()
        except FileNotFoundError:
            print("No last trace found. Run 'live' first.")
            sys.exit(1)

        print(f"--- REPLAYING TRACE: {trace_id} ---")
        replayer = Replayer(trace_id)
        io = ReplayIO(replayer)
        run_agent(io)
        print("--- REPLAY SUCCESS ---")
