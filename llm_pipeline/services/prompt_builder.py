def build_final_prompt(
    extracted_items: list[str],
    rag_context: str,
) -> str:

    return f"""You are a fuzzing engine. 
    
    You are tasked with generating 30 commands that a target would accept. 
    It is known that target accepts the following commands: {extracted_items}
    You may use the following retrieved context to generate new commands for the target: 
    {rag_context}

In the output:
- the command is the string to be sent
- the parameters are the parameters passed with the command. 
Do not invent commands and do not invent parameters.
"""