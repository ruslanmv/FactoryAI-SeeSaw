import os
import pandas as pd
import asyncio
from huggingface_hub import AsyncInferenceClient
from openai import OpenAI
import json
import re

# Load API keys
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")

client_hf = AsyncInferenceClient(HF_API_KEY)
client_openai = OpenAI(api_key=OPENAI_API_KEY)

# --- See-Saw Mechanism Functions ---

async def generate_main_or_dependency(prompt: str, use_openai=True) -> str:
    """
    Generate code using the preferred API (OpenAI or HuggingFace) based on the prompt.
    """
    try:
        if use_openai:
            completion = client_openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a code generator."},
                    {"role": "user", "content": prompt}
                ]
            )
            return completion.choices[0].message.content.strip()
        else:
            response = await client_hf.post(
                model="codellama/CodeLlama-34b-Instruct-hf",
                inputs=prompt,
                parameters={"max_new_tokens": 512, "return_full_text": False},
            )
            return response.get("generated_text", "").strip()
    except Exception as e:
        return f"Error: {e}"

def extract_code(llm_output: str) -> str:
    """
    Extract code from LLM output enclosed in triple backticks.

    Args:
        llm_output (str): The LLM output containing Markdown-formatted code.

    Returns:
        str: Extracted code blocks joined together, or a message if no code is found.
    """
    code_blocks = re.findall(r"```(?:\w+\n)?(.*?)```", llm_output, re.DOTALL)
    return "\n\n".join(block.strip() for block in code_blocks if block.strip()) or "No valid code found."

async def validator_function(main_code: str, dependency_code: str, original_description: str) -> (bool, str):
    """
    Validate compatibility of main code and dependency. Return True if compatible, else False with suggested main code.
    """
    prompt = (
        f"The following is the original project description:\n\n{original_description}\n\n"
        f"The following is the main code:\n\n{main_code}\n\n"
        f"The following is the dependency code:\n\n{dependency_code}\n\n"
        "Check compatibility. Respond 'True' if compatible, or 'False' followed by the corrected main code."
        "Ensure that the corrected main code adheres strictly to the original project description."
        "Do not include comments or explanations. Only return the raw code content."
    )
    response = await generate_main_or_dependency(prompt)
    if response.startswith("True"):
        return True, main_code
    elif response.startswith("False"):
        corrected_code = response[5:].strip()
        return False, corrected_code
    return False, f"Error in validation response: {response}"

async def see_saw_mechanism(project_tree: list):
    """
    Implement the See-Saw mechanism for generating main and dependency files.
    """
    generated_files = {}
    original_descriptions = {item['path']: item['description'] for item in project_tree}

    for item in project_tree:
        path, description = item['path'], item['description']
        if "main" in description.lower():
            # Generate main file
            main_prompt = (
                f"Generate the main file for the project:\n{description}\n\n"
                "Do not include comments or explanations. Only return the raw code content."
            )
            main_code = await generate_main_or_dependency(main_prompt)
            main_code = extract_code(main_code)
            generated_files[path] = main_code

            # Generate dependencies
            dependencies = [dep for dep in project_tree if dep['path'] != path]
            for dep in dependencies:
                dep_path, dep_desc = dep['path'], dep['description']
                dep_prompt = (
                    f"This is the main code:\n\n{main_code}\n\n"
                    f"Generate the dependency code for the file '{dep_path}':\n{dep_desc}\n\n"
                    "Do not include comments or explanations. Only return the raw code content."
                )
                dep_code = await generate_main_or_dependency(dep_prompt)
                dep_code = extract_code(dep_code)

                # Validate dependency with main code
                is_valid, updated_main_code = await validator_function(
                    main_code, dep_code, original_descriptions[path]
                )
                if not is_valid:
                    # Ensure updates respect the original functionality
                    main_code = updated_main_code
                    generated_files[path] = main_code  # Update main code
                generated_files[dep_path] = dep_code
    return generated_files

def save_generated_files(generated_files: dict, base_path: str = "./generated"):
    """
    Save all generated files to the specified base path.
    """
    for path, content in generated_files.items():
        full_path = os.path.join(base_path, path.lstrip("./"))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as file:
            file.write(content)
