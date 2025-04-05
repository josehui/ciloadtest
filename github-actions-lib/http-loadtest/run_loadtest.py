import yaml
import subprocess
import argparse
import os

DEFAULT_METHOD = "GET"
# Account for empty environment variables in Github actions
DEFAULT_RATE = os.getenv("VEGETA_RATE") or 10
DEFAULT_DURATION = os.getenv("VEGETA_DURATION") or "10s"
DEFAULT_OUTPUT_FILE = "results.txt"

def read_config(file_path):
    """Reads the YAML configuration file."""
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def run_vegeta(method, target, rate, duration, output_file):
    """Runs a Vegeta load test using the given parameters."""
    print(f"Running load test on target: {method} {target} with rate: {rate} req/s for duration: {duration}")
    vegeta_command = [
      "echo", f"{method} {target}", "|", 
      "vegeta attack", 
      "-rate", str(rate), 
      "-duration", duration, "|",
      f"vegeta report >> {output_file}"
    ]
    with open(output_file, "a") as f:
      f.write(f"Load Test Result for {method} {target}:\n-------------------\n")
    try:
      result = subprocess.run(
        " ".join(vegeta_command),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
      )
      if result.stderr:
        print(f"Error: {result.stderr}")
    except Exception as e:
      print(f"Failed to run Vegeta: {e}")
    with open(output_file, "a") as f:
      f.write("\n")

def main():
    parser = argparse.ArgumentParser(description="Run Vegeta load tests based on a YAML configuration file.")
    parser.add_argument("-c", "--config", type=str, required=True, help="Path to the YAML config file")
    parser.add_argument("-o", "--output", type=str, default=DEFAULT_OUTPUT_FILE, help="Path to the output file")
    args = parser.parse_args()

    config_path = args.config
    config = read_config(config_path)
    output_file = args.output

    for test_name, test_config in config.items():
        method = test_config.get("method", DEFAULT_METHOD)
        rate = test_config.get("rate", DEFAULT_RATE)
        duration = test_config.get("duration", DEFAULT_DURATION)

        target = test_config.get("target")
        if not target:
            print(f"Skipping test '{test_name}' due to missing 'target'")
            continue

        run_vegeta(method, target, rate, duration, output_file)

if __name__ == "__main__":
    main()
