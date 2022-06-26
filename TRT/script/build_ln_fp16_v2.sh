    /usr/local/TensorRT-8.4.1.4/bin/trtexec \
	--onnx=/root/onnx/segformer.b2.1024x1024.city.160k_replace_ln_v2.onnx \
    --fp16 \
    --minShapes=input:1x3x1024x1024 \
    --optShapes=input:4x3x1024x1024 \
    --maxShapes=input:8x3x1024x1024 \
    --workspace=23000 \
    --saveEngine=/home/pengsky/TRT-Hackathon-2022-SegFormer/TRT/engine/segFormer_ln_fp16_v2_multiStream.plan \
    --verbose \
    --tacticSources=-CUDNN,+CUBLAS \
    --streams=2 \
    --plugins=/home/pengsky/TRT-Hackathon-2022-SegFormer/TRT/LayerNormPlugin-V3.0-OneFlow-TRT8/LayerNorm.so \
    > /home/pengsky/TRT-Hackathon-2022-SegFormer/TRT/log/segformer_ln_fp16_v2_multiStream.txt
