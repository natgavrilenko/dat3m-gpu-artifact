import argparse
import os
import matplotlib.pyplot as plt

import env
from utils import Utils


class Dat3MGenerator:
    def __init__(self, model, limit):
        self.path = os.path.join(env.BENCHMARKS_DIR, "dat3m_ptx" if model == "PTX" else "dat3m_vkn")
        self.model = model
        self.limit = limit

    def generate(self):
        for pattern in ["MP", "SB", "LB", "IRIW"]:
            os.makedirs(os.path.join(self.path, pattern), exist_ok=True)
        for threads in range(2, self.limit, 1):
            with open(self.make_path("MP", threads), "w") as f:
                f.write(self.generate_mp(threads))
            with open(self.make_path("SB", threads), "w") as f:
                f.write(self.generate_sb(threads))
            with open(self.make_path("LB", threads), "w") as f:
                f.write(self.generate_lb(threads))
            with open(self.make_path("IRIW", threads), "w") as f:
                f.write(self.generate_iriw(threads))

    def make_path(self, pattern, threads):
        return os.path.join(self.path, pattern, f"{pattern}-{threads}.litmus")

    def generate_header(self, pattern, threads, regs, vars=None):
        lines = []
        lines.append(f"{self.model} {pattern}-{threads}")
        lines.append("{")
        lines = lines + (vars if vars is not None else [f"x{i}=0;" for i in range(threads)])
        lines = lines + regs
        lines.append("}")
        if self.model == "PTX":
            lines.append(" | ".join([f"P{i}@cta {i}, gpu 0" for i in range(threads)]) + " ;")
        if self.model == "Vulkan":
            lines.append(" | ".join([f"P{i}@sg 0, wg {i}, qf 0" for i in range(threads)]) + " ;")
        return lines

    def generate_mp(self, threads):
        regs = [f"P{i}:r{i}=0;" for i in range(1, threads)]
        regs.append(f"P{threads - 1}:r0=0;")
        lines = self.generate_header("MP", threads, regs)
        if self.model == "PTX":
            lines.append("st.weak x0, 1 | " + " | ".join([f"ld.acquire.gpu r{i}, x{i}" for i in range(1, threads)]) + " ;")
            lines.append(" | ".join([f"st.release.gpu x{i}, 1" for i in range(1, threads)]) + " | ld.weak r0,x0 ;")
        if self.model == "Vulkan":
            lines.append("st.sc0 x0, 1 | " + " | ".join([f"ld.atom.acq.dv.sc0.semsc0 r{i}, x{i}" for i in range(1, threads)]) + " ;")
            lines.append(" | ".join([f"st.atom.rel.dv.sc0.semsc0 x{i}, 1" for i in range(1, threads)]) + " | ld.sc0 r0,x0 ;")
        lines.append("exists\n(" + " /\\ ".join([f"P{i}:r{i} == 1" for i in range(1, threads)]) + f" /\\ P{threads - 1}:r0 == 0)")
        return "\n".join(lines)

    def generate_sb(self, threads):
        regs = [f"P{i}:r{i + 1}=0;" for i in range(threads - 1)]
        regs.append(f"P{threads - 1}:r0=0;")
        lines = self.generate_header("SB", threads, regs)
        if self.model == "PTX":
            lines.append(" | ".join([f"st.release.gpu x{i}, 1" for i in range(threads - 1)]) + f" | st.release.gpu x{threads - 1}, 1 ;")
            lines.append(" | ".join([f"ld.acquire.gpu r{i}, x{i}" for i in range(1, threads)]) + " | ld.acquire.gpu r0, x0 ;")
        if self.model == "Vulkan":
            lines.append(" | ".join([f"st.atom.rel.dv.sc0.semsc0 x{i}, 1" for i in range(threads - 1)]) + f" | st.atom.rel.dv.sc0.semsc0 x{threads - 1}, 1 ;")
            lines.append(" | ".join([f"ld.atom.acq.dv.sc0.semsc0 r{i}, x{i}" for i in range(1, threads)]) + " | ld.atom.acq.dv.sc0.semsc0 r0, x0 ;")
        lines.append("exists\n(" + " /\\ ".join([f"P{i}:r{i + 1} == 0" for i in range(threads - 1)]) + f" /\\ P{threads - 1}:r0 == 0)")
        return "\n".join(lines)

    def generate_lb(self, threads):
        regs = [f"P{i}:r{i + 1}=0;" for i in range(threads - 1)]
        regs.append(f"P{threads - 1}:r0=0;")
        lines = self.generate_header("LB", threads, regs)
        if self.model == "PTX":
            lines.append(" | ".join([f"ld.acquire.gpu r{i}, x{i}" for i in range(1, threads)]) + " | ld.acquire.gpu r0, x0 ;")
            lines.append(" | ".join([f"st.release.gpu x{i}, 1" for i in range(threads - 1)]) + f" | st.release.gpu x{threads - 1}, 1 ;")
        if self.model == "Vulkan":
            lines.append(" | ".join([f"ld.atom.acq.dv.sc0.semsc0 r{i}, x{i}" for i in range(1, threads)]) + " | ld.atom.acq.dv.sc0.semsc0 r0, x0 ;")
            lines.append(" | ".join([f"st.atom.rel.dv.sc0.semsc0 x{i}, 1" for i in range(threads - 1)]) + f" | st.atom.rel.dv.sc0.semsc0 x{threads - 1}, 1 ;")
        lines.append("exists\n(" + " /\\ ".join([f"P{i}:r{i + 1} == 1" for i in range(threads - 1)]) + f" /\\ P{threads - 1}:r0 == 1)")
        return "\n".join(lines)

    def generate_iriw(self, threads):
        half_threads = threads // 2
        vars = [f"x{i}=0;" for i in range(half_threads)]
        regs = [f"P{i}:r{j}=0;" for i in range(half_threads, threads) for j in range(half_threads)]
        lines = self.generate_header("IRIW", threads, regs, vars)
        if self.model == "PTX":
            lines.append(" | ".join([f"st.release.gpu x{i}, 1" for i in range(half_threads)]) + " | " +
                " | ".join([f"ld.acquire.gpu r{i}, x{i}" for i in range(half_threads)]) + " ;")
            for i in range(1, half_threads):
                parts = [" " for _ in range(half_threads)]
                for j in range(half_threads, threads):
                    if j == i + half_threads:
                        parts.append("ld.acquire.gpu r0, x0")
                    else:
                        parts.append(f"ld.acquire.gpu r{i}, x{i}")
                lines.append(" | ".join(parts) + " ;")
        if self.model == "Vulkan":
            lines.append(" | ".join([f"st.atom.rel.dv.sc0.semsc0 x{i}, 1" for i in range(half_threads)]) + " | " +
                " | ".join([f"ld.atom.acq.dv.sc0.semsc0 r{i}, x{i}" for i in range(half_threads)]) + " ;")
            for i in range(1, half_threads):
                parts = [" " for _ in range(half_threads)]
                for j in range(half_threads, threads):
                    if j == i + half_threads:
                        parts.append("ld.atom.acq.dv.sc0.semsc0 r0, x0")
                    else:
                        parts.append(f"ld.atom.acq.dv.sc0.semsc0 r{i}, x{i}")
                lines.append(" | ".join(parts) + " ;")
        lines.append("exists\n(" + " /\\ ".join([f"P{i}:r{j}=={1 if (i - half_threads) == j else 0}"
                for i in range(half_threads, threads)
                for j in range(half_threads)]) + ")")
        return "\n".join(lines)


class AlloyPtxGenerator:
    def __init__(self, limit):
        self.path = os.path.join(env.BENCHMARKS_DIR, "alloy_ptx")
        self.limit = limit

    def generate(self):
        for pattern in ["MP", "SB", "LB", "IRIW"]:
            os.makedirs(os.path.join(self.path, pattern), exist_ok=True)
        for threads in range(2, self.limit, 1):
            with open(self.make_path("MP", threads), "w") as f:
                f.write(self.generate_mp(threads))
            with open(self.make_path("SB", threads), "w") as f:
                f.write(self.generate_sb(threads))
            with open(self.make_path("LB", threads), "w") as f:
                f.write(self.generate_lb(threads))
            with open(self.make_path("IRIW", threads), "w") as f:
                f.write(self.generate_iriw(threads))

    def make_path(self, pattern, threads):
            return os.path.join(self.path, pattern, f"{pattern}-{threads}.test")

    def generate_header(self, vars_count):
        return [f".global x{i};" for i in range(vars_count)]

    def wrap_thread(self, thread_id, parts):
        return [f"d0.b{thread_id}.t0 {{"] + ["  " + i + ";" for i in parts] + ["}", ""]

    def generate_mp(self, threads):
        lines = self.generate_header(threads)
        lines.append("")
        lines += self.wrap_thread(0, ["st.weak [x0], 1", "st.release.gpu [x1], 1"])
        for i in range(1, threads - 1):
            lines += self.wrap_thread(i, [f"ld.acquire.gpu r{i}, [x{i}] == 1", f"st.release.gpu [x{i + 1}], 1"])
        lines += self.wrap_thread(threads - 1, [f"ld.acquire.gpu r{threads - 1}, [x{threads - 1}] == 1", "ld.weak r0, [x0]"])
        lines.append("assert (r0 == 1) as mp_transitive;")
        return "\n".join(lines)

    def generate_sb(self, threads):
        lines = self.generate_header(threads)
        lines.append("")
        for i in range(threads - 1):
            lines += self.wrap_thread(i, [f"st.release.gpu [x{i}], 1", f"ld.acquire.gpu r{i + 1}, [x{i + 1}] == 0"])
        lines += self.wrap_thread(threads - 1, [f"st.release.gpu [x{threads - 1}], 1", "ld.acquire.gpu r0, [x0]"])
        lines.append("permit (r0 == 0) as sb_transitive;")
        return "\n".join(lines)

    def generate_lb(self, threads):
        lines = self.generate_header(threads)
        lines.append("")
        for i in range(threads - 1):
            lines += self.wrap_thread(i, [f"ld.acquire.gpu r{i + 1}, [x{i + 1}] == 0", f"st.release.gpu [x{i}], 1"])
        lines += self.wrap_thread(threads - 1, ["ld.acquire.gpu r0, [x0]", f"st.release.gpu [x{threads - 1}], 1"])
        lines.append("permit (r0 == 0) as lb_transitive;")
        return "\n".join(lines)

    def generate_iriw(self, threads):
        half_threads = threads // 2
        lines = self.generate_header(half_threads)
        lines.append("")
        for i in range(half_threads):
            lines += self.wrap_thread(i, [f"st.release.gpu [x{i}], 1"])
        reg = 0
        for i in range(half_threads, threads):
            parts = []
            parts.append(f"ld.acquire.gpu r{reg}, [x{i - half_threads}] == 1")
            reg += 1
            for j in range(1, half_threads):
                if j == i - half_threads:
                    if i == threads - 1 and j == half_threads - 1:
                        parts.append(f"ld.acquire.gpu r{reg}, [x0]")
                    else:
                        parts.append(f"ld.acquire.gpu r{reg}, [x0] == 0")
                else:
                    parts.append(f"ld.acquire.gpu r{reg}, [x{j}] == 0")
                reg += 1
            lines += self.wrap_thread(i, parts)
        lines.append(f"permit (r{reg - 1} == 0) as iriw_transitive;")
        return "\n".join(lines)


class AlloyVulkanGenerator:
    def __init__(self, limit):
        self.path = os.path.join(env.BENCHMARKS_DIR, "alloy_vkn")
        self.limit = limit

    def generate(self):
        for pattern in ["MP", "SB", "LB", "IRIW"]:
            os.makedirs(os.path.join(self.path, pattern), exist_ok=True)
        for threads in range(2, self.limit, 1):
            with open(self.make_path("MP", threads), "w") as f:
                f.write(self.generate_mp(threads))
            with open(self.make_path("SB", threads), "w") as f:
                f.write(self.generate_sb(threads))
            with open(self.make_path("LB", threads), "w") as f:
                f.write(self.generate_lb(threads))
            with open(self.make_path("IRIW", threads), "w") as f:
                f.write(self.generate_iriw(threads))

    def make_path(self, pattern, threads):
        return os.path.join(self.path, pattern, f"{pattern}-{threads}.test")

    def wrap_thread(self, parts):
        return ["NEWWG", "NEWSG", "NEWTHREAD"] + parts

    def generate_mp(self, threads):
        lines = self.wrap_thread(["st.sc0 x0 = 1", "st.atom.rel.scopedev.sc0.semsc0 x1 = 1"])
        for i in range(1, threads - 1):
            lines += self.wrap_thread([f"ld.atom.acq.scopedev.sc0.semsc0 x{i} = 1", f"st.atom.rel.scopedev.sc0.semsc0 x{i + 1} = 1"])
        lines += self.wrap_thread([f"ld.atom.acq.scopedev.sc0.semsc0 x{threads - 1} = 1", "ld.sc0 x0 = 0"])
        lines.append("SATISFIABLE consistent[X]")
        return "\n".join(lines)

    def generate_sb(self, threads):
        lines = []
        for i in range(threads - 1):
            lines += self.wrap_thread([f"st.atom.rel.scopedev.sc0.semsc0 x{i} = 1", f"ld.atom.acq.scopedev.sc0.semsc0 x{i + 1} = 0"])
        lines += self.wrap_thread([f"st.atom.rel.scopedev.sc0.semsc0 x{threads - 1} = 1", "ld.atom.acq.scopedev.sc0.semsc0 x0 = 0"])
        lines.append("SATISFIABLE consistent[X]")
        return "\n".join(lines)

    def generate_lb(self, threads):
        lines = []
        for i in range(threads - 1):
            lines += self.wrap_thread([f"ld.atom.acq.scopedev.sc0.semsc0 x{i + 1} = 1", f"st.atom.rel.scopedev.sc0.semsc0 x{i} = 1"])
        lines += self.wrap_thread(["ld.atom.acq.scopedev.sc0.semsc0 x0 = 1", f"st.atom.rel.scopedev.sc0.semsc0 x{threads - 1} = 1"])
        lines.append("NOSOLUTION consistent[X]")
        return "\n".join(lines)

    def generate_iriw(self, threads):
        lines = []
        half_threads = threads // 2
        for i in range(half_threads):
            lines += self.wrap_thread([f"st.atom.rel.scopedev.sc0.semsc0 x{i} = 1"])
        for i in range(half_threads, threads):
            parts = [f"ld.atom.acq.scopedev.sc0.semsc0 x{i - half_threads} = 1"]
            for j in range(1, half_threads):
                if j == i - half_threads:
                    parts.append(f"ld.atom.acq.scopedev.sc0.semsc0 x0 = 0")
                else:
                    parts.append(f"ld.atom.acq.scopedev.sc0.semsc0 x{j} = 0")
            lines += self.wrap_thread(parts)
        lines.append("SATISFIABLE consistent[X]")
        return "\n".join(lines)


def print_table(pattern, thread_range, dat3m_ptx, dat3m_vkn, alloy_ptx, alloy_vkn):
    table = [["Threads", "Dartagnan-PTX", "Alloy-PTX", "Dartagnan-Vulkan", "Alloy-Vulkan"]]
    for threads in thread_range:
        aly_ptx = alloy_ptx[threads] if threads in alloy_ptx else None
        aly_vkn = alloy_vkn[threads] if threads in alloy_vkn else None
        table.append([threads, dat3m_ptx[threads], aly_ptx, dat3m_vkn[threads], aly_vkn])
    print(f"{pattern} Benchmarks")
    Utils.print_table(f"{pattern}.csv", table)


def print_plot(pattern, thread_range, dat3m_ptx, dat3m_vkn, alloy_ptx, alloy_vkn):
    y_dat3m_ptx = [dat3m_ptx[x] for x in thread_range]
    y_alloy_ptx = [alloy_ptx[x] for x in thread_range if x in alloy_ptx]
    y_dat3m_vkn = [dat3m_vkn[x] for x in thread_range]
    y_alloy_vkn = [alloy_vkn[x] for x in thread_range if x in alloy_vkn]

    plt.plot(thread_range, y_dat3m_ptx, '-o', label="Dartagnan-PTX")
    plt.plot([x for x in alloy_ptx], y_alloy_ptx, '-x', label="Alloy-PTX")
    plt.plot(thread_range, y_dat3m_vkn, '-o', label="Dartagnan-Vulkan")
    plt.plot([x for x in alloy_vkn], y_alloy_vkn, '-x', label="Alloy-Vulkan")

    plt.xlabel("Threads")
    plt.ylabel("Time (ms)")
    plt.title(f"{pattern} Benchmarks")
    plt.legend()
    plt.yscale("log")
    plt.savefig(os.path.join(env.OUTPUT_DIR, f"{pattern}.png"))
    plt.clf()


def run_benchmarks(pattern, thread_range):
    dat3m_ptx = {}
    path = os.path.join(env.BENCHMARKS_DIR, "dat3m_ptx")
    for threads in thread_range:
        test = os.path.join(path, pattern, f"{pattern}-{threads}.litmus")
        result = Utils.run_dartagnan_test(test, "ptx-v7.5", "program_spec", "ptx")
        if result.time is None:
            break
        dat3m_ptx[threads] = result.time

    dat3m_vkn = {}
    path = os.path.join(env.BENCHMARKS_DIR, "dat3m_vkn")
    for threads in thread_range:
        test = os.path.join(path, pattern, f"{pattern}-{threads}.litmus")
        result = Utils.run_dartagnan_test(test, "spirv", "program_spec", "vulkan")
        if result.time is None:
            break
        dat3m_vkn[threads] = result.time

    alloy_ptx = {}
    path = os.path.join(env.BENCHMARKS_DIR, "alloy_ptx")
    for threads in thread_range:
        test = os.path.join(path, pattern, f"{pattern}-{threads}.test")
        result = Utils.run_alloy_ptx_test(test)
        if result.time is None:
            break
        alloy_ptx[threads] = result.time

    alloy_vkn = {}
    path = os.path.join(env.BENCHMARKS_DIR, "alloy_vkn")
    for threads in thread_range:
        test = os.path.join(path, pattern, f"{pattern}-{threads}.test")
        result = Utils.run_alloy_vkn_test(test)
        if result.time is None:
            break
        alloy_vkn[threads] = result.time

    print_table(pattern, thread_range, dat3m_ptx, dat3m_vkn, alloy_ptx, alloy_vkn)
    print_plot(pattern, thread_range, dat3m_ptx, dat3m_vkn, alloy_ptx, alloy_vkn)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-tests", dest="generate", action="store_true")
    args = parser.parse_args()
    if args.generate:
        Dat3MGenerator("PTX", 41).generate()
        Dat3MGenerator("Vulkan", 41).generate()
        AlloyPtxGenerator(41).generate()
        AlloyVulkanGenerator(41).generate()
    else:
        run_benchmarks("SB", range(2, 41, 2))
        run_benchmarks("MP", range(2, 41, 2))
        run_benchmarks("LB", range(2, 41, 2))
        run_benchmarks("IRIW", range(4, 41, 2))


if __name__ == "__main__":
    main()
