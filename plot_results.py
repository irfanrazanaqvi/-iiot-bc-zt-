"""Generate latency-vs-concurrency and throughput-vs-concurrency figures from results.csv
for direct inclusion in Section 7 (Results) of the paper."""

import argparse

import matplotlib.pyplot as plt
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="results.csv")
    parser.add_argument("--out-prefix", default="fig")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)

    fig, ax = plt.subplots()
    ax.plot(df["concurrency"], df["latency_p50_ms"], marker="o", label="p50")
    ax.plot(df["concurrency"], df["latency_p95_ms"], marker="o", label="p95")
    ax.set_xlabel("Concurrent devices")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Authorization latency vs. concurrency")
    ax.legend()
    fig.savefig(f"{args.out_prefix}_latency.png", dpi=150, bbox_inches="tight")

    fig2, ax2 = plt.subplots()
    ax2.plot(df["concurrency"], df["throughput_rps"], marker="o", color="darkorange")
    ax2.set_xlabel("Concurrent devices")
    ax2.set_ylabel("Throughput (req/s)")
    ax2.set_title("Gateway throughput vs. concurrency")
    fig2.savefig(f"{args.out_prefix}_throughput.png", dpi=150, bbox_inches="tight")

    print("Figures written:", f"{args.out_prefix}_latency.png", f"{args.out_prefix}_throughput.png")


if __name__ == "__main__":
    main()
