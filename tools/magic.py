import os
import pandas as pd
import asyncio
from huggingface_hub import AsyncInferenceClient
from openai import OpenAI
import json
import re
import logging

import logging
import os
# Set the base folder for the generated project
current_directory = os.getcwd()
project_name = "generated"
path_project = os.path.join(current_directory, project_name)
os.makedirs(path_project, exist_ok=True)  # Ensure the folder exists
# Set up logging
log_file_path = os.path.join(path_project, "generation.log")
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler(log_file_path, mode="a"),  # Append to the shared log file
    ],
)

# Flush log file after each logging call
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.FileHandler):
        handler.flush()

# Load API keys
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")

client_hf = AsyncInferenceClient(HF_API_KEY)
client_openai = OpenAI(api_key=OPENAI_API_KEY)

# --- See-Saw Mechanism Functions ---

async def generate_main_or_dependency_old(prompt: str, use_openai=True) -> str:
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
        logging.error(f"Error generating code: {e}")
        return f"Error: {e}"

async def generate_main_or_dependency(prompt: str, use_openai=True) -> str:
    """
    Generate code using the preferred API (OpenAI or HuggingFace) based on the prompt.
    """
    global token_usage  # Add a global token usage tracker
    try:
        if use_openai:
            completion = client_openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a code generator."},
                    {"role": "user", "content": prompt}
                ]
            )
            # Track token usage from OpenAI's response
            token_usage += completion.usage.total_tokens
            return completion.choices[0].message.content.strip()
        else:
            response = await client_hf.post(
                model="codellama/CodeLlama-34b-Instruct-hf",
                inputs=prompt,
                parameters={"max_new_tokens": 512, "return_full_text": False},
            )
            # Estimate token usage for Hugging Face (adjust as needed)
            token_usage += len(prompt.split()) + len(response.get("generated_text", "").split())
            return response.get("generated_text", "").strip()
    except Exception as e:
        logging.error(f"Error generating code: {e}")
        return f"Error: {e}"




def extract_code_old(llm_output: str) -> str:
    """
    Extract code from LLM output enclosed in triple backticks.

    Args:
        llm_output (str): The LLM output containing Markdown-formatted code.

    Returns:
        str: Extracted code blocks joined together, or a message if no code is found.
    """
    code_blocks = re.findall(r"```(?:\w+\n)?(.*?)```", llm_output, re.DOTALL)
    return "\n\n".join(block.strip() for block in code_blocks if block.strip()) or "No valid code found."


def extract_code(llm_output: str) -> str:
    """
    Extract code from LLM output. If enclosed in triple backticks, strip them.
    If no backticks are present, assume the entire output is the code.
    
    Args:
        llm_output (str): The LLM output.
    
    Returns:
        str: The cleaned code.
    """
    # Try to find code blocks within triple backticks
    code_blocks = re.findall(r"```(?:\w+\n)?(.*?)```", llm_output, re.DOTALL)
    
    # If code blocks exist, use them; otherwise, assume the entire output is code
    if code_blocks:
        return "\n\n".join(block.strip() for block in code_blocks if block.strip())
    else:
        return llm_output.strip()


async def validator_function_old(main_code: str, dependency_code: str, original_description: str) -> (bool, str):
    """
    Validate compatibility of main code and dependency. Return True if compatible, else False with suggested main code.
    """
    prompt = (
        f"The following is the original project description:\n\n{original_description}\n\n"
        f"The following is the main code:\n\n{main_code}\n\n"
        f"The following is the dependency code:\n\n{dependency_code}\n\n"
        "Check compatibility. Respond 'True' if compatible, or 'False' followed by the corrected main code."
        "Ensure that the corrected main code adheres strictly to the original project description."
        "Do not include comments or explanations, and do not wrap the code in triple backticks or any other delimiters."
        "Only return the raw code content."
    )
    response = await generate_main_or_dependency(prompt)
    if response.startswith("True"):
        return True, main_code
    elif response.startswith("False"):
        corrected_code = response[5:].strip()
        return False, corrected_code
    logging.warning(f"Validation response error: {response}")
    return False, f"Error in validation response: {response}"

async def validator_function(main_code: str, dependency_code: str, original_description: str) -> (bool, str):
    """
    Validate compatibility of main code and dependency. Return True if compatible, else False with suggested main code.
    """
    global dependency_checks, aligned_dependencies
    dependency_checks += 1  # Increment the total checks
    prompt = (
        f"The following is the original project description:\n\n{original_description}\n\n"
        f"The following is the main code:\n\n{main_code}\n\n"
        f"The following is the dependency code:\n\n{dependency_code}\n\n"
        "Check compatibility. Respond 'True' if compatible, or 'False' followed by the corrected main code."
        "Ensure that the corrected main code adheres strictly to the original project description."
        "Do not include comments or explanations, and do not wrap the code in triple backticks or any other delimiters."
        "Only return the raw code content."
    )
    response = await generate_main_or_dependency(prompt)
    if response.startswith("True"):
        aligned_dependencies += 1  # Increment aligned dependencies count
        return True, main_code
    elif response.startswith("False"):
        corrected_code = response[5:].strip()
        return False, corrected_code
    logging.warning(f"Validation response error: {response}")
    return False, f"Error in validation response: {response}"





async def see_saw_mechanism_old(project_tree: list):
    """
    Implement the See-Saw mechanism for generating main and dependency files.
    """
    generated_files = {}
    original_descriptions = {item['path']: item['description'] for item in project_tree}

    for item in project_tree:
        path, description = item['path'], item['description']
        if "main" in description.lower():
            logging.info(f"Generating main file: {path}")
            main_prompt = (
                f"Generate the main file for the project:\n{description}\n\n"
                "Do not include comments or explanations, and do not wrap the code in triple backticks or any other delimiters. "
                "Only return the raw code content."
            )
            main_code = await generate_main_or_dependency(main_prompt)
            main_code = extract_code(main_code)
            generated_files[path] = main_code

            dependencies = [dep for dep in project_tree if dep['path'] != path]
            for dep in dependencies:
                dep_path, dep_desc = dep['path'], dep['description']
                logging.info(f"Generating dependency: {dep_path}")
                dep_prompt = (
                    f"This is the main code:\n\n{main_code}\n\n"
                    f"Generate the dependency code for the file '{dep_path}':\n{dep_desc}\n\n"
                    "Do not include comments or explanations. Only return the raw code content."
                )
                dep_code = await generate_main_or_dependency(dep_prompt)
                dep_code = extract_code(dep_code)

                is_valid, updated_main_code = await validator_function(
                    main_code, dep_code, original_descriptions[path]
                )
                if not is_valid:
                    logging.warning(f"Main code updated for compatibility with {dep_path}")
                    main_code = updated_main_code
                    generated_files[path] = main_code
                else:
                    logging.info(f"Dependency {dep_path} validated successfully without updating main code.")
                generated_files[dep_path] = dep_code
    return generated_files

import time
async def see_saw_mechanism_partial(project_tree: list):
    """
    Implement the See-Saw mechanism for generating main and dependency files.
    """
    import time

    # Initialize metrics
    global token_usage, dependency_checks, aligned_dependencies
    token_usage = 0
    dependency_checks = 0
    aligned_dependencies = 0

    generated_files = {}
    original_descriptions = {item['path']: item['description'] for item in project_tree}

    # Start timing the process
    start_time = time.time()

    for item in project_tree:
        path, description = item['path'], item['description']

        if "main" in description.lower():
            logging.info(f"Generating main file: {path}")
            try:
                main_prompt = (
                    f"Generate the main file for the project:\n{description}\n\n"
                    "Do not include comments or explanations. Only return the raw code content."
                )
                main_code = await generate_main_or_dependency(main_prompt)



                
                token_usage += len(main_prompt.split())  # Track token usage
                main_code = extract_code(main_code)
                generated_files[path] = main_code
            except Exception as e:
                logging.error(f"Error generating code: {e}")
                continue

            dependencies = [dep for dep in project_tree if dep['path'] != path]
            for dep in dependencies:
                dep_path, dep_desc = dep['path'], dep['description']
                logging.info(f"Generating dependency: {dep_path}")
                try:
                    dep_prompt = (
                        f"This is the main code:\n\n{main_code}\n\n"
                        f"Generate the dependency code for the file '{dep_path}':\n{dep_desc}\n\n"
                        "Do not include comments or explanations. Only return the raw code content."
                    )
                    dep_code = await generate_main_or_dependency(dep_prompt)
                    token_usage += len(dep_prompt.split())  # Track token usage
                    dep_code = extract_code(dep_code)

                    # Validate dependency alignment
                    dependency_checks += 1
                    is_valid, updated_main_code = await validator_function(
                        main_code, dep_code, original_descriptions[path]
                    )
                    if is_valid:
                        aligned_dependencies += 1
                        logging.info(f"Dependency {dep_path} validated successfully without updating main code.")
                    else:
                        logging.warning(f"Main code updated for compatibility with {dep_path}")
                        main_code = updated_main_code
                        generated_files[path] = main_code
                    generated_files[dep_path] = dep_code
                except Exception as e:
                    logging.error(f"Error generating code: {e}")
                    continue

    # End timing and calculate execution time
    execution_time = time.time() - start_time

    return generated_files, execution_time


import time
import logging

async def see_saw_mechanism_new1(project_tree: list):
    """
    Implement the See-Saw mechanism for generating main and dependency files.
    """
    # Initialize metrics
    global token_usage, dependency_checks, aligned_dependencies
    token_usage = 0
    dependency_checks = 0
    aligned_dependencies = 0

    generated_files = {}
    original_descriptions = {item['path']: item['description'] for item in project_tree}
    total_token_usage = []  # List to track all token usages

    # Start timing the process
    start_time = time.time()

    for item in project_tree:
        path, description = item['path'], item['description']

        if "main" in description.lower():
            logging.info(f"Generating main file: {path}")
            try:
                main_prompt = (
                    f"Generate the main file for the project:\n{description}\n\n"
                    "Do not include comments or explanations. Only return the raw code content."
                )
                main_code = await generate_main_or_dependency(main_prompt)

                # Track token usage
                token_usage_main = len(main_code.split())
                logging.info(f"token_usage_main: {token_usage_main}")
                total_token_usage.append(token_usage_main)
                
                main_code = extract_code(main_code)
                generated_files[path] = main_code
            except Exception as e:
                logging.error(f"Error generating code: {e}")
                continue

            dependencies = [dep for dep in project_tree if dep['path'] != path]
            for dep in dependencies:
                dep_path, dep_desc = dep['path'], dep['description']
                logging.info(f"Generating dependency: {dep_path}")
                try:
                    dep_prompt = (
                        f"This is the main code:\n\n{main_code}\n\n"
                        f"Generate the dependency code for the file '{dep_path}':\n{dep_desc}\n\n"
                        "Do not include comments or explanations. Only return the raw code content."
                    )
                    dep_code = await generate_main_or_dependency(dep_prompt)
                    
                    # Track token usage
                    token_usage_dep = len(dep_code.split())
                    logging.info(f"token_usage_dep: {token_usage_dep}")
                    total_token_usage.append(token_usage_dep)

                    dep_code = extract_code(dep_code)

                    # Validate dependency alignment
                    dependency_checks += 1
                    is_valid, updated_main_code = await validator_function(
                        main_code, dep_code, original_descriptions[path]
                    )
                    if is_valid:
                        aligned_dependencies += 1
                        logging.info(f"Dependency {dep_path} validated successfully without updating main code.")
                    else:
                        logging.warning(f"Main code updated for compatibility with {dep_path}")
                        main_code = updated_main_code
                        generated_files[path] = main_code
                    generated_files[dep_path] = dep_code
                except Exception as e:
                    logging.error(f"Error generating code: {e}")
                    continue

    # End execution timer
    execution_time = time.time() - start_time

    # Calculate total token usage
    total_token_value = sum(total_token_usage)

    # Create metrics dictionary
    metrics = {
            "token_usage": total_token_value,
            "alignment": (aligned_dependencies / dependency_checks) * 100 if dependency_checks > 0 else 0,
            "execution_time": execution_time,
        
    }
    print("metrics see-saw",metrics)
    return "Project built successfully!", generated_files, metrics


import time
import logging

async def see_saw_mechanism(project_tree: list):
    """
    Implement the See-Saw mechanism for generating main and dependency files.
    """
    # Initialize metrics
    global token_usage, dependency_checks, aligned_dependencies
    token_usage = 0
    dependency_checks = 0
    aligned_dependencies = 0

    generated_files = {}
    original_descriptions = {item['path']: item['description'] for item in project_tree}
    iteration_metrics = []  # List to store metrics for each iteration

    # Start timing the process
    start_time = time.time()

    iteration = 1  # Initialize iteration counter

    for item in project_tree:
        path, description = item['path'], item['description']

        if "main" in description.lower():
            logging.info(f"Generating main file: {path}")
            try:
                main_prompt = (
                    f"Generate the main file for the project:\n{description}\n\n"
                    "Do not include comments or explanations. Only return the raw code content."
                )
                iteration_start = time.time()  # Start iteration timing
                main_code = await generate_main_or_dependency(main_prompt)

                # Track token usage
                token_usage_main = len(main_code.split())
                logging.info(f"token_usage_main: {token_usage_main}")
                main_code = extract_code(main_code)
                generated_files[path] = main_code

                # Append iteration metrics
                iteration_metrics.append({
                    "iteration": iteration,
                    "type": "main",
                    "token_usage": token_usage_main,
                    "execution_time": time.time() - iteration_start
                })
                iteration += 1  # Increment iteration counter
            except Exception as e:
                logging.error(f"Error generating code: {e}")
                continue

            dependencies = [dep for dep in project_tree if dep['path'] != path]
            for dep in dependencies:
                dep_path, dep_desc = dep['path'], dep['description']
                logging.info(f"Generating dependency: {dep_path}")
                try:
                    dep_prompt = (
                        f"This is the main code:\n\n{main_code}\n\n"
                        f"Generate the dependency code for the file '{dep_path}':\n{dep_desc}\n\n"
                        "Do not include comments or explanations. Only return the raw code content."
                    )
                    iteration_start = time.time()  # Start iteration timing
                    dep_code = await generate_main_or_dependency(dep_prompt)

                    # Track token usage
                    token_usage_dep = len(dep_code.split())
                    logging.info(f"token_usage_dep: {token_usage_dep}")
                    dep_code = extract_code(dep_code)

                    # Validate dependency alignment
                    dependency_checks += 1
                    is_valid, updated_main_code = await validator_function(
                        main_code, dep_code, original_descriptions[path]
                    )
                    if is_valid:
                        aligned_dependencies += 1
                        logging.info(f"Dependency {dep_path} validated successfully without updating main code.")
                    else:
                        logging.warning(f"Main code updated for compatibility with {dep_path}")
                        main_code = updated_main_code
                        generated_files[path] = main_code
                    generated_files[dep_path] = dep_code

                    # Append iteration metrics
                    iteration_metrics.append({
                        "iteration": iteration,
                        "type": "dependency",
                        "token_usage": token_usage_dep,
                        "execution_time": time.time() - iteration_start
                    })
                    iteration += 1  # Increment iteration counter
                except Exception as e:
                    logging.error(f"Error generating code: {e}")
                    continue

    # End execution timer
    execution_time_total = time.time() - start_time

    # Calculate total token usage
    total_token_usage = sum([metric["token_usage"] for metric in iteration_metrics])

    # Create metrics dictionary
    metrics = {
        "token_usage_total": total_token_usage,
        "alignment": (aligned_dependencies / dependency_checks) * 100 if dependency_checks > 0 else 0,
        "execution_time_total": execution_time_total,
        "iterations": iteration_metrics
    }

    print("metrics see-saw", metrics)
    return "Project built successfully!", generated_files, metrics




def save_generated_files(generated_files: dict, base_path: str = "./generated"):
    """
    Save all generated files to the specified base path.
    """
    for path, content in generated_files.items():
        full_path = os.path.join(base_path, path.lstrip("./"))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as file:
            file.write(content)
        logging.info(f"File saved: {full_path}")
