#!/usr/bin/python
import os
import sys
import ctypes
import numpy as np
from glob import glob 
from time import time_ns
from datetime import datetime as dt
from cuda import cudart
import tensorrt as trt

dataFilePath = "/home/pengsky/TRT-Hackathon-2022-SegFormer/TRT/data/"
planFilePath   = "/home/pengsky/TRT-Hackathon-2022-SegFormer/TRT/engine/"
soFilePath = "/home/pengsky/TRT-Hackathon-2022-SegFormer/TRT/LayerNormPlugin-V3.0-OneFlow-TRT8/"

logFilePath = "/home/pengsky/TRT-Hackathon-2022-SegFormer/TRT/log/"

# for test engine 
segFormerPlanFile  = planFilePath + "segFormer.plan" # fp32-no-plugin ok
segFormerPlanFile  = planFilePath + "segFormer_fp16.plan" # fp16-no-plugin ok
segFormerPlanFile  = planFilePath + "segFormer_ln_best_v2.plan" # int8-partial-plugin ok
segFormerPlanFile  = planFilePath + "segFormer_ln_fp16_patial.plan" # fp16-partial-plugin ok
segFormerPlanFile  = planFilePath + "segFormer_ln_fp16_v2.plan" # fp16-with-plugin ok


segFormerScoreFile = logFilePath + "encoderScore.txt"
soFileList = glob(soFilePath + "*.so")


tableHead = \
"""
bs: Batch Size
lt: Latency (ms)
tp: throughput (img/s)
a0: maximum of absolute difference of output 0
r0: median of relative difference of output 0
----+--------+---------+---------+---------+-------------
  bs|      lt|       tp|       a0|       r0| output check
----+--------+---------+---------+---------+-------------
"""

def printArrayInfo(x, description=""):
    print( '%s: %s\n  Mean=%.5e,SumAbs=%.5e,Var=%.5e,Max=%.5f,Min=%.5f,SAD=%.5e'%( \
        description,str(x.shape),np.mean(x),np.sum(abs(x)),np.var(x),np.max(x),np.min(x),np.sum(np.abs(np.diff(x.reshape(-1)))) ))
    print("\t", x.reshape(-1)[:10])

def check(a, b, weak=False, epsilon = 1e-5):

    if weak:
        res = np.all( np.abs(a - b) < epsilon )
    else:
        res = np.all( a == b )

    # diff0 = np.max(np.abs(a - b))
    # 修改了diff0的计算方式，使之更贴合语义分割
    diff0 = np.sum(a!=b) / np.prod(a.shape)
    diff1 = np.median(np.abs(a - b) / (np.abs(b) + epsilon))
    return res, diff0, diff1

#-------------------------------------------------------------------------------
logger = trt.Logger(trt.Logger.ERROR)
trt.init_libnvinfer_plugins(logger, '')

if len(soFileList) > 0:
    print("Find Plugin %s!"%soFileList)
else:
    print("No Plugin!")
for soFile in soFileList:
    ctypes.cdll.LoadLibrary(soFile)

#-------------------------------------------------------------------------------

print("Test segFormer Part!")

with open(segFormerScoreFile, 'w') as f:

    if os.path.isfile(segFormerPlanFile):
        with open(segFormerPlanFile, 'rb') as segFormerF:
            engine = trt.Runtime(logger).deserialize_cuda_engine(segFormerF.read())
        if engine is None:
            print("Failed loading %s"%segFormerPlanFile)
            exit()
        print("Succeeded loading %s"%segFormerPlanFile)
    else:
        print("Failed finding %s"%segFormerPlanFile)
        exit()

    nInput = np.sum([ engine.binding_is_input(i) for i in range(engine.num_bindings) ])
    nOutput = engine.num_bindings - nInput
    context = engine.create_execution_context()
        
    print(tableHead)  # for standard output

    for ioFile in sorted(glob(dataFilePath + "./segformer-*.npz")):
        ioData = np.load(ioFile)
        # print(ioData)
        input = ioData['input']

        batchSize, _, _, _ = input.shape
        if batchSize > 8:
            continue

        context.set_binding_shape(0, input.shape)

        
        bufferH = []
        bufferH.append(input.astype(np.float32).reshape(-1) )

        for i in range(nInput, nInput + nOutput):                
            bufferH.append( np.empty(context.get_binding_shape(i), dtype=trt.nptype(engine.get_binding_dtype(i))) )

        bufferD = []
        for i in range(nInput + nOutput):                
            bufferD.append( cudart.cudaMalloc(bufferH[i].nbytes)[1] )

        for i in range(nInput):
            cudart.cudaMemcpy(bufferD[i], bufferH[i].ctypes.data, bufferH[i].nbytes, cudart.cudaMemcpyKind.cudaMemcpyHostToDevice)

        context.execute_v2(bufferD)

        for i in range(nInput, nInput + nOutput):
            cudart.cudaMemcpy(bufferH[i].ctypes.data, bufferD[i], bufferH[i].nbytes, cudart.cudaMemcpyKind.cudaMemcpyDeviceToHost)

        # warm up
        for i in range(10):
            context.execute_v2(bufferD)

        # test infernece time
        t0 = time_ns()
        for i in range(30):
            context.execute_v2(bufferD)
        t1 = time_ns()
        timePerInference = (t1-t0)/1000/1000/30

        indexEncoderOut = engine.get_binding_index('output')
        
        check0 = check(bufferH[indexEncoderOut],ioData['output'],True,5e-5)

        string = "%4d,%8.3f,%9.3e,%9.3e,%9.3e"%(batchSize,
                                                    timePerInference,
                                                    batchSize/timePerInference*1000,
                                                    check0[1],
                                                    check0[2])
        
        print(string + ", %s"%("Good" if check0[1] < 1e-4 and check0[2] < 2e-3 else "Bad"))
        f.write(string + "\n")

        for i in range(nInput + nOutput):                
            cudart.cudaFree(bufferD[i])



# output_list = ['404', '613', '859', '1053', '1300', '1532', '1741', '1987', '2234', '2466', '2721']
