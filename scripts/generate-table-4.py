import os

import env
from utils import Utils


def get_dat3m_tests():
    return Utils.list_files(os.path.join(env.DAT3M_HOME, "dartagnan/src/test/resources/spirv/gpuverify"), "spv.dis")


def get_gpuverify_tests():
    all = Utils.list_files(os.path.join(env.GPU_VERIFY_HOME, "latest_benchmarks/OpenCL/"), ".cl")
    with open(os.path.join(env.FILTER_DIR, "clspv-compilation-filter.txt"), "r") as f:
        filter = [os.path.join(env.GPU_VERIFY_HOME, test.strip()) for test in f.readlines()]
    return [test for test in all if test not in filter]


def main():
    table = [["Tool", "Tests", "Time", "Time/Tests"]]

    tests = get_dat3m_tests()
    time = sum([Utils.run_dartagnan_test(test, "spirv", "cat_spec", "vulkan").time for test in tests])
    table.append(["\\dartagnan", len(tests), f"{time:.0f}", f"{(time / len(tests)):.0f}"])

    tests = get_gpuverify_tests()
    time = sum([Utils.run_gpuverify_test(test).time for test in tests])
    table.append(["\\gpuverify", len(tests), f"{time:.0f}", f"{(time / len(tests)):.0f}"])

    Utils.print_table("table4.csv", table)


if __name__ == "__main__":
    main()
