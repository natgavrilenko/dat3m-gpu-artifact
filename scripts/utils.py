from abc import ABC
import os
import re
import csv
import subprocess
from tabulate import tabulate
import time

import env


class Result(ABC):
    def __init__(self, time, out, err):
        self.time = None
        self.out = out
        self.err = err
        if "java.lang.OutOfMemoryError: Java heap space" not in err:
            self.time = int(time)


class Dat3MResult(Result):
    re_result_str = re.compile(r'Verification finished with result (FAIL|PASS|UNKNOWN)')
    re_result_val = re.compile(r'(FAIL|PASS|UNKNOWN)')
    re_time_str = re.compile(r'Total verification time: (\d+.\d* secs|\d+:\d+ mins|\d+:\d+:\d+ hours)')
    re_time_val_sec = re.compile(r'\d+.\d*')
    re_time_val_min = re.compile(r'\d+:\d+')
    re_time_val_hour = re.compile(r'\d+:\d+:\d+')
    re_events_str = [
        re.compile(r'#Annotations: \d+'),
        re.compile(r'#Stores: \d+'),
        re.compile(r'#Loads: \d+'),
        re.compile(r'#Inits: \d+'),
        re.compile(r'#Others: \d+')
    ]
    re_events_val = re.compile(r'\d+'),

    def __init__(self, time, out, err):
        super().__init__(time, out, err)
        if self.time is not None:
            self.result = self.parse_result()
            self.parsed_time = self.parse_time()
            self.events = self.parse_events()

    def parse_result(self):
        match1 = re.search(self.re_result_str, self.out)
        if match1 is not None:
            match2 = re.search(self.re_result_val, match1[0])
            if match2 is not None:
                return match2[0]
        raise ValueError("Cannot find verification result")

    def parse_time(self):
        match = re.search(self.re_time_str, self.out)
        if match is not None:
            if "secs" in match[0]:
                return self.parse_seconds(match[0])
            if "mins" in match[0]:
                return self.parse_minutes(match[0])
            if "hours" in match[0]:
                return self.parse_hours(match[0])
        raise ValueError("Cannot find verification time")

    def parse_seconds(self, raw):
        match = re.search(self.re_time_val_sec, raw)
        if match is not None:
            return float(match[0]) * 1000
        raise ValueError("Malformed verification time seconds")

    def parse_minutes(self, raw):
        match = re.search(self.re_time_val_min, raw)
        if match is not None:
            parts = match[0].split(":")
            return (int(parts[0]) * 60 + int(parts[1])) * 1000
        raise ValueError("Malformed verification time minutes")

    def parse_hours(self, raw):
        match = re.search(self.re_time_val_hour, raw)
        if match is not None:
            parts = match[0].split(":")
            return (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
        raise ValueError("Malformed verification time hours")

    def parse_events(self):
        events = 0
        for regex in self.re_events_str:
            events += self.parse_event_type(regex)
        return events

    def parse_event_type(self, regex):
        match1 = re.search(regex, self.out)
        if match1 is not None:
            match2 = re.search(r'\d+', match1[0])
            if match2 is not None:
                return int(match2[0])
        raise ValueError("Cannot find event count")


class AlloyPtxResult(Result):
    re_result_fail = re.compile(r'breaks expectation')
    re_result_pass = re.compile(r'(matches expectation|outcome permitted)')

    def __init__(self, time, out, err):
        super().__init__(time, out, err)
        if self.time is not None:
            self.result = self.parse_result()

    def parse_result(self):
        if re.search(self.re_result_fail, self.out) is not None:
            return "FAIL"
        if re.search(self.re_result_pass, self.out) is not None:
            return "PASS"
        raise ValueError("Cannot find verification result")


class AlloyVknResult(Result):
    re_result_fail = re.compile(r'Test \S+.test.gen failed')

    def __init__(self, time, out, err):
        super().__init__(time, out, err)
        if self.time is not None:
            self.result = self.parse_result()

    def parse_result(self):
        if re.search(self.re_result_fail, self.out) is not None:
            return "FAIL"
        return "PASS"


class GPUVerifyResult(Result):
    re_result_str = re.compile(r'GPUVerify kernel analyser finished with \d+ verified, \d+ error')
    re_result_pass = re.compile(r' 0 error')

    def __init__(self, time, out, err):
        super().__init__(time, out, err)
        if self.time is not None:
            if "Stack dump:" in err:
                self.result = "FAIL"
            else:
                self.result = self.parse_result()
            self.time = int(time)

    def parse_result(self):
        match1 = re.search(self.re_result_str, self.out)
        if match1 is not None:
            match2 = re.search(self.re_result_pass, match1[0])
            if match2 is not None:
                return "PASS"
        return "FAIL"


class Utils:
    @staticmethod
    def list_files(path, ext):
        return [os.path.join(dp, f) for dp, dn, filenames in os.walk(path) for f in filenames if f.endswith(ext)]

    @staticmethod
    def run_command(command):
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True) as p:
            out, err = p.communicate()
        return out.decode("utf-8"), err.decode("utf-8")

    @staticmethod
    def run_dartagnan_test(test, cat, property, target, bound=1):
        command = (f"cd {env.DAT3M_HOME} && java -jar dartagnan/target/dartagnan.jar "
                        f"{test} cat/{cat}.cat --property={property} --target={target} "
                        f"--bound={bound} --encoding.integers=true --method=assume")
        start = time.time()
        out, err = Utils.run_command(command)
        return Dat3MResult((time.time() - start) * 1000, out, err)

    @staticmethod
    def run_alloy_ptx_test(test):
        command = f"python3 {os.path.join(env.ALLOY_PTX_HOME, 'src/test_to_alloy.py')} {test}"
        start = time.time()
        out, err = Utils.run_command(command)
        return AlloyPtxResult((time.time() - start) * 1000, out, err)

    @staticmethod
    def run_alloy_vkn_test(test):
        command = f"make -j4 -C {env.ALLOY_VKN_HOME} runtests TEST_FILE={test}"
        start = time.time()
        out, err = Utils.run_command(command)
        return AlloyVknResult((time.time() - start) * 1000, out, err)

    @staticmethod
    def run_gpuverify_test(test):
        parts = [os.path.join(env.GPU_VERIFY_HOME, "gpuverify")]
        with open(test, "r") as f:
            f.readline()
            parts += f.readline().strip().strip("//").split(" ")
        parts.append(test)
        command = " ".join(parts)
        start = time.time()
        out, err = Utils.run_command(command)
        return GPUVerifyResult((time.time() - start) * 1000, out, err)

    @staticmethod
    def print_table(filename, table):
        print(tabulate(table[1:], headers=table[0]))
        os.makedirs(env.OUTPUT_DIR, exist_ok=True)
        path = os.path.join(env.OUTPUT_DIR, filename)
        with open(path, "w") as f:
            csv.writer(f).writerows(table)
        print(f"Table written to {path}")
