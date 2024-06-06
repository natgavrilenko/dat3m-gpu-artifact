FROM ubuntu:22.04
ARG DEBIAN_FRONTEND=noninteractive

# Update Ubuntu Software repository
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    software-properties-common \
    git \
    vim \
    sudo \
    wget \
    unzip \
    maven \
    make \
    g++ \
    openjdk-17-jdk \
    openjdk-17-jre \
    python3 \
    python3-pip \
    python-is-python3 \
    libncurses5 && \
    rm -rf /var/lib/apt/lists/*

ENV DAT3M_HOME=/home/Dat3M
ENV DAT3M_OUTPUT=$DAT3M_HOME/output
ENV _JAVA_OPTIONS="-Xmx4g"

# Install Dat3M
WORKDIR /home
RUN git clone --branch spirv-visitor --shallow-since 2024-05-30 https://github.com/hernanponcedeleon/Dat3M && \
    cd Dat3M && \
    git checkout bfd85bbe7712ce2c9d29c532d31dff0c2b341553 && \
    mvn clean install -DskipTests

# Install mono
RUN gpg --homedir /tmp --no-default-keyring \
    --keyring /usr/share/keyrings/mono-official-archive-keyring.gpg \
    --keyserver hkp://keyserver.ubuntu.com:80 \
    --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF
RUN echo "deb [signed-by=/usr/share/keyrings/mono-official-archive-keyring.gpg] \
    https://download.mono-project.com/repo/ubuntu stable-focal main" | \
    sudo tee /etc/apt/sources.list.d/mono-official-stable.list
RUN apt-get update && apt-get install -y mono-devel

# Install gpu-verify
WORKDIR /home
RUN wget https://github.com/mc-imperial/gpuverify/releases/download/2018-03-22/GPUVerifyLinux64.zip
RUN unzip GPUVerifyLinux64.zip
RUN mv 2018-03-22 gpuverify-release
RUN rm GPUVerifyLinux64.zip
# Get latest testsuite from gpuverify github
RUN git clone --branch master --shallow-since 2022-07-27 https://github.com/mc-imperial/gpuverify.git && \
    cd gpuverify && \
    git checkout 49219770aad01231edd0d8e0fa3ed036006cf32a
RUN mv /home/gpuverify/testsuite /home/gpuverify-release/latest_benchmarks
RUN pip3 install psutil

# Install mixedproxy
WORKDIR /home
RUN pip3 install lark-parser
RUN git clone --branch benchmarks --shallow-since 2023-11-13 https://github.com/tonghaining/mixedproxy.git && \
    cd /home/mixedproxy && \
    git checkout 1ed863119576c55cc7f6d83bf71a7cb630877834 && \
    make

# Install Vulkan-MemoryModel
WORKDIR /home
RUN git clone --branch benchmarks --shallow-since 2024-05-29 https://github.com/tonghaining/Vulkan-MemoryModel.git && \
    cd Vulkan-MemoryModel && \
    git checkout 6c89eae2665f596eab68714ec4d8f1eb08b66903

WORKDIR /home/Vulkan-MemoryModel/alloy
ENV VKN_ALLOY_JAR=org.alloytools.alloy.dist-5.0.0-20190619.101010-34.jar
RUN wget https://oss.sonatype.org/content/repositories/snapshots/org/alloytools/org.alloytools.alloy.dist/5.0.0-SNAPSHOT/${VKN_ALLOY_JAR}
RUN make -j4

# Install artifact
WORKDIR /home
RUN git clone https://github.com/natgavrilenko/dat3m-gpu-artifact.git

# Copy scripts and configuration
RUN cp -r /home/dat3m-gpu-artifact/scripts /home
RUN cp -r /home/dat3m-gpu-artifact/templates /home
RUN cp -r /home/dat3m-gpu-artifact/filter /home

# Copy binaries of Spir-V compiler and Spir-V disassembler
# We use precompiled binaries because compilation takes hours
RUN unzip /home/dat3m-gpu-artifact/bin/clspv.zip -d /bin
RUN unzip /home/dat3m-gpu-artifact/bin/spirv-dis.zip -d /bin

# Delete artifact folder
RUN rm -rf /home/dat3m-gpu-artifact

# Install python tools to generate tables
RUN pip3 install tabulate
RUN pip3 install matplotlib

# Generate benchmarks
RUN python3 /home/scripts/generate-table-5.py --generate
RUN python3 /home/scripts/generate-plots.py --generate
