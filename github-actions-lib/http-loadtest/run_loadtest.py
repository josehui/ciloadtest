import yaml
import subprocess
import argparse
import os
import json
import matplotlib.pyplot as plt
import requests
from datetime import datetime

DEFAULT_METHOD = "GET"
DEFAULT_RATE = os.getenv("VEGETA_RATE") or 10
DEFAULT_DURATION = os.getenv("VEGETA_DURATION") or "10s"
DEFAULT_OUTPUT_FILE = "results.md"
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")


def read_config(file_path):
    """Reads the YAML configuration file."""
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def run_vegeta(method, target, rate, duration, output_file):
    """Runs a Vegeta load test using the given parameters."""
    print(
        f"Running load test on target: {method} {target} with rate: {rate} req/s for duration: {duration}"
    )

    # Create the Vegeta attack command
    attack_command = (
        f"echo '{method} {target}' | vegeta attack -rate={rate} -duration={duration}"
    )
    report_command = "vegeta report -type=json"

    try:
        # Run the Vegeta attack and pipe the output to the report command
        attack_process = subprocess.Popen(
            attack_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        report_process = subprocess.run(
            report_command,
            shell=True,
            stdin=attack_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        attack_process.stdout.close()

        if report_process.stderr:
            print(f"Error: {report_process.stderr}")
            return

        # Parse the JSON output from Vegeta
        report_json = json.loads(report_process.stdout)

        # Convert the JSON report to Markdown
        markdown_report = convert_json_to_markdown(
            report_json, method, target, rate, duration
        )

        # Append the Markdown report to the output file
        with open(output_file, "a") as f:
            f.write(markdown_report)
            f.write("\n")

    except Exception as e:
        print(f"Failed to run Vegeta: {e}")


def convert_json_to_markdown(report_json, method, target, rate, duration):
    """Converts Vegeta JSON report to Markdown table format."""
    markdown = []
    markdown.append(f"## Load Test Report for {method} {target}")
    markdown.append(f"**Target:** `{method} {target}`")
    markdown.append(f"**Rate:** `{rate} req/s`")
    markdown.append(f"**Duration:** `{duration}`")
    markdown.append("")
    markdown.append(f"### Metrics")
    markdown.append(f"| Metric                  | Value                          |")
    markdown.append(f"|-------------------------|--------------------------------|")
    markdown.append(f"| **Requests**            | {report_json.get('requests', 0)} |")
    markdown.append(
        f"| **Success Rate**        | {report_json.get('success', 0) * 100:.2f}% |"
    )
    markdown.append(
        f"| **Latency (mean)**      | {report_json.get('latencies', {}).get('mean', 0) / 1e6:.2f} ms |"
    )
    markdown.append(
        f"| **Latency (50th)**      | {report_json.get('latencies', {}).get('50th', 0) / 1e6:.2f} ms |"
    )
    markdown.append(
        f"| **Latency (95th)**      | {report_json.get('latencies', {}).get('95th', 0) / 1e6:.2f} ms |"
    )
    markdown.append(
        f"| **Latency (max)**       | {report_json.get('latencies', {}).get('max', 0) / 1e6:.2f} ms |"
    )
    markdown.append(
        f"| **Bytes In (total)**    | {report_json.get('bytes_in', {}).get('total', 0)} bytes |"
    )
    markdown.append(
        f"| **Bytes Out (total)**   | {report_json.get('bytes_out', {}).get('total', 0)} bytes |"
    )
    markdown.append("")
    return "\n".join(markdown)


def upload_to_imgur(image_path):
    """Uploads an image to Imgur and returns the image URL."""
    if not IMGUR_CLIENT_ID:
        print("IMGUR_CLIENT_ID is not set")
        return None

    headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
    with open(image_path, "rb") as image_file:
        response = requests.post(
            "https://api.imgur.com/3/image",
            headers=headers,
            files={"image": image_file},
        )
    if response.status_code == 200:
        return response.json()["data"]["link"]
    else:
        print(f"Failed to upload image to Imgur: {response.status_code}")
        return None


def calculate_min_max_usage(file_path):
    """Calculates the minimum and maximum CPU and memory usage for each pod."""
    if not os.path.exists(file_path):
        print(f"File '{file_path}' does not exist.")
        return {}

    usage_data = {}

    with open(file_path, "r") as file:
        if not file:
            print(f"File '{file_path}' is empty.")
            return
        for line in file:
            entry = json.loads(line)
            for pod, usage in entry["usage"].items():
                if pod not in usage_data:
                    usage_data[pod] = {"cpu": [], "memory": []}
                usage_data[pod]["cpu"].append(usage["cpu"])
                usage_data[pod]["memory"].append(usage["memory"])

    min_max_data = {}
    for pod, data in usage_data.items():
        min_max_data[pod] = {
            "min_cpu": min(data["cpu"]),
            "max_cpu": max(data["cpu"]),
            "min_memory": min(data["memory"]),
            "max_memory": max(data["memory"]),
        }

    return min_max_data


def append_min_max_to_markdown(min_max_data, output_file):
    """Appends the minimum and maximum CPU and memory usage to the Markdown report."""
    markdown = []
    markdown.append("")
    markdown.append(
        "| Pod Name       | Min CPU (mC) | Max CPU (mC) | Min Memory (MiB) | Max Memory (MiB) |"
    )
    markdown.append(
        "|----------------|--------------|--------------|------------------|------------------|"
    )

    for pod, data in min_max_data.items():
        markdown.append(
            f"| {pod} | {data['min_cpu']} | {data['max_cpu']} | {data['min_memory']} | {data['max_memory']} |"
        )
    markdown.append("")
    with open(output_file, "a") as file:
        file.write("\n".join(markdown))
        file.write("\n")


def plot_usage_from_file(file_path, output_file):
    """Plots CPU and memory usage from a JSON file and appends the Imgur links to the Markdown report."""
    if not os.path.exists(file_path):
        print(f"File '{file_path}' does not exist.")
        return

    # Read data from the file
    cpu_data = {}
    memory_data = {}
    timestamps = []

    with open(file_path, "r") as file:
        if not file:
            print(f"File '{file_path}' is empty.")
            return
        for line in file:
            entry = json.loads(line)
            timestamps.append(entry["timestamp"])
            for pod, usage in entry["usage"].items():
                if pod not in cpu_data:
                    cpu_data[pod] = []
                    memory_data[pod] = []
                cpu_data[pod].append((entry["timestamp"], usage["cpu"]))
                memory_data[pod].append((entry["timestamp"], usage["memory"]))

    start_time = datetime.fromtimestamp(timestamps[0]).strftime("%Y-%m-%d %H:%M:%S")
    end_time = datetime.fromtimestamp(timestamps[-1]).strftime("%Y-%m-%d %H:%M:%S")
    x_label = (
        f"Time (seconds since monitoring start)\nStart: {start_time}, End: {end_time}"
    )

    # Normalize timestamps
    # Plot CPU usage
    cpu_plot_path = "cpu_usage.png"
    plt.figure(figsize=(12, 6))
    for pod, metric in cpu_data.items():
        ts = [m[0] - timestamps[0] for m in metric]
        cpu_values = [m[1] for m in metric]
        plt.plot(ts, cpu_values, label=f"{pod} CPU (mC)")
    plt.ylabel("CPU Usage (millicores)")
    plt.xlabel(x_label)
    plt.legend()
    plt.grid()
    plt.title("CPU Usage Over Time")
    plt.savefig(cpu_plot_path, format="png", bbox_inches="tight")
    plt.close()

    # Plot Memory usage
    memory_plot_path = "memory_usage.png"
    plt.figure(figsize=(12, 6))
    for pod, metric in memory_data.items():
        ts = [m[0] - timestamps[0] for m in metric]
        memory_values = [m[1] for m in metric]
        plt.plot(ts, memory_values, label=f"{pod} Memory (MiB)")
    plt.ylabel("Memory Usage (MiB)")
    plt.xlabel(x_label)
    plt.legend()
    plt.grid()
    plt.title("Memory Usage Over Time")
    plt.savefig(memory_plot_path, format="png", bbox_inches="tight")
    plt.close()

    # Upload plots to Imgur
    cpu_imgur_url = upload_to_imgur(cpu_plot_path)
    memory_imgur_url = upload_to_imgur(memory_plot_path)

    # Append the Imgur links to the Markdown report
    with open(output_file, "a") as f:
        f.write(f"![CPU Usage]({cpu_imgur_url})\n")
        f.write(f"![Memory Usage]({memory_imgur_url})\n")
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Run Vegeta load tests and optionally plot resource usage."
    )
    parser.add_argument(
        "-c", "--config", type=str, required=True, help="Path to the YAML config file"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_FILE,
        help="Path to the output file",
    )
    parser.add_argument(
        "-m",
        "--monitor",
        type=str,
        help="Path to the resource usage JSON file from monitor script",
    )
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

    # If a monitor file is provided, plot the resource usage and append to the Markdown report
    if args.monitor:
        with open(output_file, "a") as f:
            f.write(f"## Resource Usage\n")
        # Calculate and append min/max usage to markdown report
        min_max_data = calculate_min_max_usage(args.monitor)
        append_min_max_to_markdown(min_max_data, output_file)
        # Plot usage and upload to Imgur
        plot_usage_from_file(args.monitor, output_file)


if __name__ == "__main__":
    main()
