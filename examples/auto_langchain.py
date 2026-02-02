import agenttrace
from langchain_community.llms import FakeListLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. Enable auto-instrumentation
agenttrace.instrument()

def main():
    # Setup LangChain (LCEL Style)
    llm = FakeListLLM(responses=["Paris"])
    prompt = PromptTemplate.from_template("What is the capital of {country}?")
    chain = prompt | llm | StrOutputParser()

    # 2. Start tracing scope
    print("Starting trace...")
    with agenttrace.trace("auto_langchain_demo") as t:
        # 3. Run Chain (should be auto-captured)
        print("Running Chain...")
        result = chain.invoke({"country": "France"})
        print(f"Result: {result}")

if __name__ == "__main__":
    main()
