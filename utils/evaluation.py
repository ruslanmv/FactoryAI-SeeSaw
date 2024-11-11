import os
import csv
import datetime

# Define base path for evaluation
def create_evaluation_directory():
    base_path = "./evaluation/build"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    eval_path = os.path.join(base_path, timestamp)

    os.makedirs(eval_path, exist_ok=True)

    return eval_path

def write_csv(file_path, data, headers):
    """
    Write data to a CSV file.
    """
    with open(file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)  # Write header
        writer.writerows(data)  # Write rows

def generate_evaluation_csv(eval_path, metrics):
    """
    Generate evaluation CSV files in the specified folder.

    Args:
        eval_path: Path to save the evaluation files.
        metrics: A dictionary containing evaluation metrics.
    """
    # Data for token usage
    token_usage_data = [
        ["Method", "Token Usage (Tokens)"],
        ["See-Saw", metrics["seesaw"]["token_usage_total"]],
        ["Standard", metrics["standard"]["token_usage_total"]]
    ]
    write_csv(os.path.join(eval_path, "token_usage.csv"), token_usage_data[1:], token_usage_data[0])

    # Data for dependency alignment
    alignment_data = [
        ["Method", "Dependency Alignment (%)"],
        ["See-Saw", metrics["seesaw"]["alignment"]],
        ["Standard", metrics["standard"]["alignment"]]
    ]
    write_csv(os.path.join(eval_path, "alignment.csv"), alignment_data[1:], alignment_data[0])

    # Data for execution time
    execution_time_data = [
        ["Method", "Execution Time (Seconds)"],
        ["See-Saw", metrics["seesaw"]["execution_time_total"]],
        ["Standard", metrics["standard"]["execution_time_total"]]
    ]
    write_csv(os.path.join(eval_path, "execution_time.csv"), execution_time_data[1:], execution_time_data[0])

    # Data for iterations (token usage and execution time per iteration)
    tokens_data = [["Method", "Iteration", "Type", "Token Usage", "Execution Time"]]
    for method, method_data in metrics.items():
        for iteration in method_data["iterations"]:
            tokens_data.append([
                "See-Saw" if method == "seesaw" else "Standard",
                iteration["iteration"],
                iteration["type"],
                iteration["token_usage"],
                iteration["execution_time"]
            ])
    write_csv(os.path.join(eval_path, "tokens.csv"), tokens_data[1:], tokens_data[0])

def main(metrics):
    """
    Main function to generate evaluation CSV files.

    Args:
        metrics: A dictionary containing evaluation metrics.

    Example of metrics:
        metrics = {
            "seesaw": {
                "token_usage_total": 600000,
                "alignment": 98,
                "execution_time_total": 120,
                "iterations": [
                    {"iteration": 1, "type": "main", "token_usage": 2000, "execution_time": 10},
                    {"iteration": 2, "type": "dependency", "token_usage": 1000, "execution_time": 10}
                ]
            },
            "standard": {
                "token_usage_total": 1000000,
                "alignment": 75,
                "execution_time_total": 115,
                "iterations": [
                    {"iteration": 1, "type": "main", "token_usage": 2000, "execution_time": 10},
                    {"iteration": 2, "type": "dependency", "token_usage": 1000, "execution_time": 10}
                ]
            }
        }
    """
    eval_path = create_evaluation_directory()
    generate_evaluation_csv(eval_path, metrics)
    print(f"Evaluation CSV files generated in {eval_path}")

if __name__ == "__main__":
    # Example metrics for testing
    example_metrics = {
        "seesaw": {
            "token_usage_total": 600000,
            "alignment": 98,
            "execution_time_total": 120,
            "iterations": [
                {"iteration": 1, "type": "main", "token_usage": 2000, "execution_time": 10},
                {"iteration": 2, "type": "dependency", "token_usage": 1000, "execution_time": 10}
            ]
        },
        "standard": {
            "token_usage_total": 1000000,
            "alignment": 75,
            "execution_time_total": 115,
            "iterations": [
                {"iteration": 1, "type": "main", "token_usage": 2000, "execution_time": 10},
                {"iteration": 2, "type": "dependency", "token_usage": 1000, "execution_time": 10}
            ]
        }
    }
    main(example_metrics)
