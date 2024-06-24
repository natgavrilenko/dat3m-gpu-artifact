import argparse
import os
import shutil

import env
from utils import Utils


data = [
    { "name": "caslock", "grid": [2, 3], "bound": 2 },
    { "name": "caslock-acq2rx", "grid": [4, 2], "bound": 1 },
    { "name": "caslock-rel2rx", "grid": [4, 2], "bound": 1 },
    { "name": "caslock-dv2wg", "grid": [4, 1], "bound": 2 },
    { "name": "caslock-dv2wg", "grid": [4, 2], "bound": 1 },

    { "name": "ticketlock", "grid": [2, 3], "bound": 1 },
    { "name": "ticketlock-acq2rx", "grid": [4, 2], "bound": 1 },
    { "name": "ticketlock-rel2rx", "grid": [4, 2], "bound": 1 },
    { "name": "ticketlock-dv2wg", "grid": [4, 1], "bound": 2 },
    { "name": "ticketlock-dv2wg", "grid": [4, 2], "bound": 1 },

    { "name": "ttaslock", "grid": [2, 2], "bound": 4 },
    { "name": "ttaslock-acq2rx", "grid": [4, 2], "bound": 1 },
    { "name": "ttaslock-rel2rx", "grid": [4, 2], "bound": 1 },
    { "name": "ttaslock-dv2wg", "grid": [4, 1], "bound": 4 },
    { "name": "ttaslock-dv2wg", "grid": [4, 2], "bound": 1 },

    { "name": "xf-barrier", "grid": [3, 3], "bound": 9 },
    { "name": "xf-barrier-acq2rx-1", "grid": [2, 2], "bound": 4 },
    { "name": "xf-barrier-acq2rx-2", "grid": [2, 2], "bound": 4 },
    { "name": "xf-barrier-rel2rx-1", "grid": [2, 2], "bound": 4 },
    { "name": "xf-barrier-rel2rx-2", "grid": [2, 2], "bound": 4 },
]


def get_template_filename(entry):
    return os.path.join(env.TEMPLATES_DIR, entry["name"] + ".spv.dis")


def get_benchmark_filename(entry):
    return os.path.join(env.BENCHMARKS_DIR, "spirv",
        entry["name"] + "-" + str(entry["grid"][0] * entry["grid"][1]) + ".spv.dis")


def format_result(result):
    if result == "PASS":
        return "\\cmark"
    if result == "FAIL":
        return "\\xmark"
    raise ValueError(f"Invalid verification result: {result}")


def generate_benchmarks():
    os.makedirs(os.path.join(env.BENCHMARKS_DIR, "spirv"), exist_ok=True)
    for entry in data:
        with open(get_template_filename(entry), "r") as f_src:
            with open(get_benchmark_filename(entry), "w") as f_dst:
                f_dst.write(f"; @Config: {entry['grid'][0]}, 1, {entry['grid'][1]}\n")
                f_dst.write(f_src.read())


def run_benchmarks():
    table = [["Program", "Grid", "Threads", "Events", "Result", "Time"]]
    for entry in data:
        path = get_benchmark_filename(entry)
        result = Utils.run_dartagnan_test(path, "spirv", "cat_spec", "vulkan", bound=entry["bound"])
        table.append([
                    entry['name'],
                    f"{entry['grid'][0]}.{entry['grid'][1]}",
                    f"{entry['grid'][0] * entry['grid'][1]}",
                    result.events,
                    format_result(result.result),
                    f"{result.time:.0f}"
                ])
    Utils.print_table("table7.csv", table)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-tests", dest="generate", action="store_true")
    args = parser.parse_args()
    if args.generate:
        generate_benchmarks()
    else:
        run_benchmarks()


if __name__ == "__main__":
    main()
