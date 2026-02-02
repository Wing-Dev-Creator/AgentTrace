from __future__ import annotations

from typing import TypedDict

from agenttrace import Tracer
from agenttrace.langchain import AgentTraceCallbackHandler

try:
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.graph import END, StateGraph
except Exception as exc:  # pragma: no cover - optional dependency
    raise SystemExit("Install langgraph and langchain-core to run this example.") from exc


class State(TypedDict):
    messages: list


def echo_node(state: State) -> State:
    return {"messages": state["messages"] + [AIMessage(content="hi")]}


if __name__ == "__main__":
    tracer = Tracer(trace_name="langgraph_basic")
    handler = AgentTraceCallbackHandler(tracer)

    builder = StateGraph(State)
    builder.add_node("echo", echo_node)
    builder.set_entry_point("echo")
    builder.add_edge("echo", END)
    app = builder.compile()

    with tracer:
        app.invoke(
            {"messages": [HumanMessage(content="hello")]},
            config={"callbacks": [handler]},
        )
