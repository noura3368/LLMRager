def build_final_prompt_generate(
    extracted_items: list[str],
    rag_context: str,
    number_of_commands: int = 10,
) -> str:

    return f"""You are a fuzzing engine. 
    
    You are tasked with generating {str(number_of_commands)} commands that a target would accept for fuzzing. 
    It is known that target accepts the following commands: {extracted_items}
    You may use your own internal knowledge and the following retrieved context to generate NEW commands for the target: 
    {rag_context}

In the output:
- the command is the string to be sent
- the parameters are the parameters passed with the command. 
Do not invent commands and do not invent parameters unless they are valid.
You are allowed to return parameters, but do not return parameters that would change the state of the system.
"""


def build_final_prompt_modify(
    extracted_items: list[str],
    rag_context: str,
    number_of_commands: int = 10,
) -> str:

    return f"""You are a fuzzing engine. 
    
    You are tasked with generating {str(number_of_commands)} commands that a target would accept for fuzzing. 
    It is known that target accepts the following commands: {extracted_items}
    You may use your own internal knowledge and the following retrieved context to modify the following commands: {extracted_items} for the target: 
    {rag_context}

In the output:
- the command is the string to be sent
- the parameters are the parameters passed with the command. 
Do not invent commands and do not invent parameters unless they are valid.
You are allowed to return parameters, but do not return parameters that would change the state of the system.
"""