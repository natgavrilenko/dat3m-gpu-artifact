# Towards Unified Analysis of GPU Consistency (Artifact)

This artifact accompanies the paper
"Towards Unified Analysis of GPU Consistency"
by Haining Tong, Natalia Gavrilenko, Hernán Ponce de León, and Keijo Heljanko.
It contains a Dockerfile that installs all tools, scrips, and data
required to reproduce the experiments in the paper.

### Building

Building a docker image:
```
docker build . -t dat3m-gpu-artifact
```
Running a docker container:
```
docker run -ti --rm dat3m-gpu-artifact
```

### Reproducing results with ready scripts

Commands:
```
python3 /home/scripts/generate-table-3.py
python3 /home/scripts/generate-table-4.py
python3 /home/scripts/generate-table-5.py
python3 /home/scripts/generate-plots.py
```

### Running individual tests

**Running a litmus test with dartagnan**

Command:
```
cd /home/Dat3M && java -jar dartagnan/target/dartagnan.jar \
<path/to/test.litmus> \
<cat/ptx-v6.0.cat|cat/ptx-v7.5.cat|cat/spirv.cat> \
--property=<program_spec|cat_spec|liveness> \
--target=<ptx|vulkan> \
--method=assume
```

Example:
```
cd /home/Dat3M && java -jar dartagnan/target/dartagnan.jar \
litmus/PTX/Manual/MP-gpu.litmus \
cat/ptx-v7.5.cat \
--property=program_spec \
--target=ptx \
--method=assume

cd /home/Dat3M && java -jar dartagnan/target/dartagnan.jar \
litmus/VULKAN/Data-Race/mp-filter.litmus \
cat/spirv.cat \
--property=cat_spec \
--target=vulkan \
--method=assume

cd /home/Dat3M && java -jar dartagnan/target/dartagnan.jar \
litmus/VULKAN/CADP/2_threads_2_instructions/4_simple.litmus \
cat/spirv.cat \
--property=liveness \
--target=vulkan \
--method=assume
```

Options:
- `<path/to/test.litmus>` path to a litmus test file
- `<cat/ptx-v6.0.cat|cat/ptx-v7.5.cat|cat/spirv.cat>` path to a consistency model file
    - `cat/ptx-v6.0.cat` ptx model v6.0 (for ptx tests)
    - `cat/ptx-v7.5.cat` ptx model v7.5 (for ptx tests)
    - `cat/spirv.cat` vulkan model (for vulkan tests)
- `property=<program_spec|cat_spec|liveness>` verification property
    - `program_spec` assertions on final state (default)
    - `cat_spec` data-race freedom
    - `liveness` termination guarantees
- `target=<ptx|vulkan>` target architecture (must agree with test type)
    - `ptx` for ptx tests
    - `vulkan` for vulkan tests

Tests:
- `/home/Dat3M/litmus/PTX`
- `/home/Dat3M/litmus/VULKAN`
- `/home/benchmarks/dat3m_ptx`
- `/home/benchmarks/dat3m_vkn`

**Running a spirv test with dartagnan**

Command:
```
cd /home/Dat3M && java -jar dartagnan/target/dartagnan.jar \
<path/to/test.spv.dis> \
cat/spirv.cat \
--property=<program_spec|cat_spec|liveness> \
--bound=<loop-bound> \
--target=vulkan \
--encoding.integers=true \
--method=assume
```

Example:
```
cd /home/Dat3M && java -jar dartagnan/target/dartagnan.jar \
/home/benchmarks/spirv/xf-barrier-9.spv.dis \
cat/spirv.cat \
--property=cat_spec \
--target=vulkan \
--bound=9 \
--encoding.integers=true \
--method=assume
```

Options:
- `<path/to/test.spv.dis>` path to a test file
- `property=<program_spec|cat_spec|liveness>` verification property
    - `program_spec` assertions on final state (default)
    - `cat_spec` data-race freedom
    - `liveness` termination guarantees
- `bound=<loop-bound>` unrolling bound for all loops (default 1)

Tests:
- `/home/Dat3M/dartagnan/src/test/resources/spirv`
- `/home/benchmarks/spirv`

**Running a ptx test with alloy**

Command:
```
cd /home/mixedproxy && src/test_to_alloy.py <path/to/test.test>
```

Example:
```
cd /home/mixedproxy && src/test_to_alloy.py /home/mixedproxy/tests/MP_gpu.test
```

Tests:
- `/home/mixedproxy/tests`
- `/home/benchmarks/alloy_ptx`


**Running a vulkan test with alloy**

Command:
```
cd /home/Vulkan-MemoryModel/alloy && \
java -cp "org.alloytools.alloy.dist-5.0.0-20190619.101010-34.jar:." \
RunCommandLine <path/to/test.test.gen>
```

Example:
```
cd /home/Vulkan-MemoryModel/alloy && \
java -cp "org.alloytools.alloy.dist-5.0.0-20190619.101010-34.jar:." \
RunCommandLine /home/Vulkan-MemoryModel/alloy/build/mp.test.gen
```

Tests:
- `/home/Vulkan-MemoryModel/alloy/build`
- `/home/benchmarks/alloy_vkn`

**Running an opencl test with gpuverify**

Command:
```
python3 /home/gpuverify-release/GPUVerify.py \
--local_size=<local-size> \
--global_size=<global-size> \
--no-benign-tolerance \
<path/to/test.cl>
```

Example:
```
python3 /home/gpuverify-release/GPUVerify.py \
--local_size=1024 \
--global_size=2048 \
--no-benign-tolerance \
/home/Dat3M/benchmarks/opencl/caslock-gpu-verify.cl
```

Options:
- `<local-size>` number of threads in workgroup
- `<global-size>` total number of threads (should be a multiple of `local-size`)
- `<path/to/test.cl>` path to the test file

Tests:
- `/home/gpuverify-release/testsuite/OpenCL`
- `/home/Dat3M/benchmarks/opencl/`

**Compiling and disassembling opencl kernels**

Command:
```
clspv <path/to/test.cl> \
--cl-std=CL2.0 --inline-entry-points \
--spv-version=1.6 -o kernel.spv
spirv-dis kernel.spv > kernel.spv.dis
rm kernel.spv
```

Example:
```
clspv /home/Dat3M/benchmarks/opencl/xf-barrier.cl \
--cl-std=CL2.0 --inline-entry-points \
--spv-version=1.6 -o kernel.spv
spirv-dis kernel.spv > kernel.spv.dis
rm kernel.spv
```

Tests:
- `/home/gpuverify-release/testsuite/OpenCL`
- `/home/Dat3M/benchmarks/opencl`

*Generating test configuration:*
In addition to the spirv code itself,
dartagnan expects the configuration of the test as part of its input.
This configuration is given as a comment
at the top of a disassembled spirv file and should be generated manually.
Dartagnan expects the following configuration parameters:

- `@Config (x, y, z)` threads hierarchy (default 1, 1, 1)
    - `x` the number of threads in a subgroup
    - `y` the number of subgroups in a workgroup
    - `z` the number of workgroups in a queue family
- `@Input` values normally passed from a host to a device via a shared buffer (mandatory for runtime array variable type)
- `@Output` assertions on the output values (mandatory for `program_spec` verification property)

Example:
```
; @Input: %17 = {{0}}
; @Input: %18 = {{0}}
; @Input: %19 = {{-1, -1}}
; @Output: forall (%19[0][0] != %19[0][1])
; @Config: 4, 1, 2
```
