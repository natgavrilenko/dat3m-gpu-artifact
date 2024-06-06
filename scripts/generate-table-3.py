import os

import env
from utils import Utils


def run_dartagnan_tests(path, cat, property, target):
    with open(os.path.join("/home/Dat3M/dartagnan/src/test/resources/", path), "r") as f:
        lines = (line.rstrip() for line in f)
        tests = [line.split(",")[0] for line in lines if line]
    time = sum([Utils.run_dartagnan_test(test, cat, property, target).time for test in tests])
    return time, len(tests)


def run_ptx_alloy_tests():
    tests = Utils.list_files(os.path.join(env.ALLOY_PTX_HOME, "tests"), ".test")
    time = 0
    count = 0
    for test in tests:
        result = Utils.run_alloy_ptx_test(test)
        time += result.time
        count += result.out.count("Launching Alloy...")
    return time, count


def run_vulkan_alloy_tests():
    tests = Utils.list_files(os.path.join(env.ALLOY_VKN_HOME, "tests"), ".test")
    time = sum([Utils.run_alloy_vkn_test(test).time for test in tests])
    safety_check = 0
    dr_check = 0
    for file in tests:
        with open(file, "r") as f:
            for line in f.readlines():
                if "#dr=0" in line:
                    safety_check += 1
                elif "#dr>0" in line:
                    dr_check += 1
                elif "NOSOLUTION" in line or "SATISFIABLE" in line:
                    safety_check += 1
    return time, safety_check, dr_check


def main():
    # Run Alloy Dat3M
    dat3m_ptx60_safety_time, dat3m_ptx60_safety_size = run_dartagnan_tests(
        "PTXv6_0-expected.csv", "ptx-v6.0", "program_spec", "ptx")
    dat3m_ptx75_safety_time, dat3m_ptx75_safety_size = run_dartagnan_tests(
        "PTXv7_5-expected.csv", "ptx-v7.5", "program_spec", "ptx")
    dat3m_ptx60_liveness_time, dat3m_ptx60_liveness_size = run_dartagnan_tests(
        "PTXv6_0-Liveness-expected.csv", "ptx-v6.0", "liveness", "ptx")
    dat3m_ptx75_liveness_time, dat3m_ptx75_liveness_size = run_dartagnan_tests(
        "PTXv7_5-Liveness-expected.csv", "ptx-v7.5", "liveness", "ptx")

    dat3m_ptx60_total_size = dat3m_ptx60_safety_size + dat3m_ptx60_liveness_size
    dat3m_ptx60_total_time = dat3m_ptx60_safety_time + dat3m_ptx60_liveness_time
    dat3m_ptx60_total_average = dat3m_ptx60_total_time / dat3m_ptx60_total_size
    dat3m_ptx75_total_size = dat3m_ptx75_safety_size + dat3m_ptx75_liveness_size
    dat3m_ptx75_total_time = dat3m_ptx75_safety_time + dat3m_ptx75_liveness_time
    dat3m_ptx75_total_average = dat3m_ptx75_total_time / dat3m_ptx75_total_size

    dat3m_vkn_safety_time, dat3m_vkn_safety_size = run_dartagnan_tests(
        "VULKAN-expected.csv", "spirv", "program_spec", "vulkan")
    dat3m_vkn_safety_time_nochains, dat3m_vkn_safety_size_nochains = run_dartagnan_tests(
        "VULKAN-NOCHAINS-expected.csv", "spirv-nochains", "program_spec", "vulkan")
    dat3m_vkn_liveness_time, dat3m_vkn_liveness_size = run_dartagnan_tests(
        "VULKAN-Liveness-expected.csv", "spirv", "liveness", "vulkan")
    dat3m_vkn_dr_time, dat3m_vkn_dr_size = run_dartagnan_tests(
        "VULKAN-DR-expected.csv", "spirv", "cat_spec", "vulkan")
    dat3m_vkn_dr_time_nochains, dat3m_vkn_dr_size_nochains = run_dartagnan_tests(
        "VULKAN-DR-NOCHAINS-expected.csv", "spirv-nochains", "cat_spec", "vulkan")

    dat3m_vkn_safety_time += dat3m_vkn_safety_time_nochains
    dat3m_vkn_safety_size += dat3m_vkn_safety_size_nochains
    dat3m_vkn_dr_time += dat3m_vkn_dr_time_nochains
    dat3m_vkn_dr_size += dat3m_vkn_dr_size_nochains

    dat3m_vkn_total_size = dat3m_vkn_safety_size + dat3m_vkn_liveness_size + dat3m_vkn_dr_size
    dat3m_vkn_total_time = dat3m_vkn_safety_time + dat3m_vkn_liveness_time + dat3m_vkn_dr_time
    dat3m_vkn_total_average = dat3m_vkn_total_time / dat3m_vkn_total_size

    # Run Alloy PTX
    alloy_ptx75_total_time, alloy_ptx75_safety_size = run_ptx_alloy_tests()
    alloy_ptx75_total_size = alloy_ptx75_safety_size
    alloy_ptx75_total_average = alloy_ptx75_total_time / alloy_ptx75_total_size

    # Run Alloy Vulkan
    alloy_vkn_total_time, alloy_vkn_safety_size, alloy_vkn_dr_size = run_vulkan_alloy_tests()
    alloy_vkn_total_size = alloy_vkn_safety_size + alloy_vkn_dr_size
    alloy_vkn_total_average = alloy_vkn_total_time / alloy_vkn_total_size

    table = [
        ["Tool", "Model", "Safety", "Liveness", "DRF", "Total", "Time", "Time/Tests"],
        ["\\dartagnan", "PTX6.0", dat3m_ptx60_safety_size, dat3m_ptx60_liveness_size, 0, dat3m_ptx60_total_size,
         f"{dat3m_ptx60_total_time:.0f}", f"{dat3m_ptx60_total_average:.0f}"],
        ["\\alloy", "PTX6.0", 0, 0, 0, 0, 0, 0],
        ["\\dartagnan", "PTX7.5", dat3m_ptx75_safety_size, dat3m_ptx75_liveness_size, 0, dat3m_ptx75_total_size,
         f"{dat3m_ptx75_total_time:.0f}", f"{dat3m_ptx75_total_average:.0f}"],
        ["\\alloy", "PTX7.5", alloy_ptx75_safety_size, 0, 0, alloy_ptx75_total_size,
         f"{alloy_ptx75_total_time:.0f}", f"{alloy_ptx75_total_average:.0f}"],
        ["\\dartagnan", "Vulkan", dat3m_vkn_safety_size, dat3m_vkn_liveness_size, dat3m_vkn_dr_size,
         dat3m_vkn_total_size, f"{dat3m_vkn_total_time:.0f}", f"{dat3m_vkn_total_average:.0f}"],
        ["\\alloy", "Vulkan", alloy_vkn_safety_size, 0, alloy_vkn_dr_size, alloy_vkn_total_size,
         f"{alloy_vkn_total_time:.0f}", f"{alloy_vkn_total_average:.0f}"],
    ]

    Utils.print_table("table3.csv", table)


if __name__ == "__main__":
    main()
