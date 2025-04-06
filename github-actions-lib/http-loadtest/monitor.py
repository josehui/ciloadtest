import time
import subprocess
import json
import argparse

# Function to query Metrics Server and fetch pod metrics for a specific namespace
def fetch_metrics(namespace):
    try:
        result = subprocess.run(
            ["kubectl", "get", "--raw", f"/apis/metrics.k8s.io/v1beta1/namespaces/{namespace}/pods"],
            capture_output=True,
            text=True
        )
        metrics = json.loads(result.stdout)
        return metrics
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return None

# Function to extract CPU and memory usage for specific pods
def extract_usage(metrics, pod_names=None):
    usage_data = {}
    for pod in metrics.get("items", []):
        pod_name = pod["metadata"]["name"]
        if pod_names is None or pod_name in pod_names:
            cpu = pod["containers"][0]["usage"]["cpu"]
            memory = pod["containers"][0]["usage"]["memory"]
            usage_data[pod_name] = {
                "cpu": convert_cpu_to_millicores(cpu),
                "memory": convert_memory_to_megabytes(memory)
            }
    return usage_data

# Helper functions to convert CPU and memory units
def convert_cpu_to_millicores(cpu):
    if cpu.endswith("n"):
        return int(cpu[:-1]) / 1e6  # Convert nanocores to millicores
    elif cpu.endswith("m"):
        return int(cpu[:-1])  # Already in millicores
    else:
        return int(cpu) * 1000  # Convert cores to millicores

def convert_memory_to_megabytes(memory):
    if memory.endswith("Ki"):
        return int(memory[:-2]) / 1024  # Convert KiB to MiB
    elif memory.endswith("Mi"):
        return int(memory[:-2])  # Already in MiB
    elif memory.endswith("Gi"):
        return int(memory[:-2]) * 1024  # Convert GiB to MiB
    else:
        return int(memory) / (1024 * 1024)  # Assume bytes, convert to MiB

# Periodically query metrics and store data
def monitor_pods(namespace, pod_names, interval, duration, output_file):
    end_time = time.time() + duration

    with open(output_file, "a") as file:  # Open in append mode
      while time.time() < end_time:
        metrics = fetch_metrics(namespace)
        if metrics:
          usage = extract_usage(metrics, pod_names)
          timestamp = time.time()
          # Write the timestamp and usage data as a single line
          file.write(json.dumps({"timestamp": timestamp, "usage": usage}) + "\n")
          file.flush()
        time.sleep(interval)
    return
    

def generate_markdown_report(data, output_file):
    """Generates a Markdown report with min and max CPU and memory usage."""
    markdown = []
    markdown.append("# Resource Usage Report")
    markdown.append("")
    markdown.append("| Pod Name       | Min CPU (mC) | Max CPU (mC) | Min Memory (MiB) | Max Memory (MiB) |")
    markdown.append("|----------------|--------------|--------------|------------------|------------------|")

    for pod, usage in data.items():
        min_cpu = min(usage["cpu"])
        max_cpu = max(usage["cpu"])
        min_memory = min(usage["memory"])
        max_memory = max(usage["memory"])
        markdown.append(f"| {pod} | {min_cpu} | {max_cpu} | {min_memory} | {max_memory} |")

    markdown.append("")

    with open(output_file, "a") as file:
        file.write("\n".join(markdown))
        file.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor pod resource usage.")
    parser.add_argument("namespace", type=str, help="Namespace to monitor")
    parser.add_argument("interval", type=int, help="Interval between queries (seconds)")
    parser.add_argument("duration", type=int, help="Duration to monitor (seconds)")
    parser.add_argument("output_file", type=str, help="File to save usage data and report")
    parser.add_argument("--pods", nargs="*", help="Specific pod names to monitor (default: all pods in namespace)")
    args = parser.parse_args()

    namespace = args.namespace
    interval = args.interval
    duration = args.duration
    output_file = args.output_file
    pod_names = args.pods  # None if not provided, meaning all pods will be monitored

    monitor_pods(namespace, pod_names, interval, duration, output_file)
