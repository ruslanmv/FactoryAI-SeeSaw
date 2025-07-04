import os
import sys
import pandas as pd

def count_lines(content):
    """
    Count the number of lines in the given content.

    Args:
        content (str): The content to count lines in.

    Returns:
        int: The number of lines.
    """
    if isinstance(content, str):
        return content.count('\n') + 1  # Count newline characters and add 1 for the last line
    return 0  # Return 0 if content is not a string (e.g., error message)

def display_and_store_directory_content(base_path):
    """
    Display all paths with directories and files along with their content, 
    and store the information in a Pandas DataFrame.

    Args:
        base_path (str): The root directory path to scan.

    Returns:
        None: Prints paths and content, and saves the DataFrame as a pickle file.
    """
    data = []  # To store path, content, and line count as rows for the DataFrame

    for root, dirs, files in os.walk(base_path):
        # Store directories (no content)
        for d in dirs:
            dir_path = os.path.join(root, d)
            data.append({"path": dir_path, "content": "", "lines": 0})
            print(f"Directory: {dir_path}")

        # Store files and their content
        for f in files:
            file_path = os.path.join(root, f)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
            except Exception as e:
                content = f"Error reading file: {e}"
            
            # Count lines in the content
            line_count = count_lines(content)
            
            data.append({"path": file_path, "content": content, "lines": line_count})
            print(f"\nFile: {file_path}")
            print("-" * 40)
            print(content)
            print(f"- Number of lines: {line_count}")
            print("-" * 40)

    # Create a DataFrame
    df = pd.DataFrame(data)

    # Create the 'extraction' directory if it doesn't exist
    extraction_dir = "extraction"
    if not os.path.exists(extraction_dir):
        os.makedirs(extraction_dir)

    # Use the last component of the base path as the file name
    base_name = os.path.basename(os.path.normpath(base_path))
    output_file = os.path.join(extraction_dir, f"{base_name}.pkl")

    # Save the DataFrame to a pickle file
    df.to_pickle(output_file)
    print(f"\nDataFrame saved to {output_file}")

if __name__ == "__main__":
    # Ensure a directory path is provided as an argument
    if len(sys.argv) < 2:
        print("Usage: python utils\\extract_all_content.py <directory>")
        sys.exit(1)

    # Get the directory path from the command-line arguments
    directory_path = sys.argv[1]

    # Execute the function
    if os.path.exists(directory_path):
        display_and_store_directory_content(directory_path)
    else:
        print(f"Error: The path '{directory_path}' does not exist.")
